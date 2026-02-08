#!/bin/bash
# scripts/deploy.sh
# Complete deployment script for Django on AWS EKS
# This script guides you through the entire setup process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking required dependencies..."
    
    local deps=("aws" "kubectl" "helm" "terraform" "docker")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        log_info "Please install missing dependencies and try again"
        exit 1
    fi
    
    log_info "All dependencies installed ✓"
}

configure_aws() {
    log_info "Configuring AWS credentials..."
    
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        log_info "Run: aws configure"
        exit 1
    fi
    
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=${AWS_REGION:-us-east-1}
    
    log_info "AWS Account ID: $AWS_ACCOUNT_ID"
    log_info "AWS Region: $AWS_REGION"
}

create_terraform_backend() {
    log_info "Creating Terraform backend (S3 + DynamoDB)..."
    
    BUCKET_NAME="terraform-state-${AWS_ACCOUNT_ID}"
    TABLE_NAME="terraform-state-lock"
    
    # Create S3 bucket
    if ! aws s3 ls "s3://${BUCKET_NAME}" 2>&1 > /dev/null; then
        log_info "Creating S3 bucket: $BUCKET_NAME"
        aws s3 mb "s3://${BUCKET_NAME}" --region "$AWS_REGION"
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "$BUCKET_NAME" \
            --versioning-configuration Status=Enabled
        
        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "$BUCKET_NAME" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
        
        log_info "S3 bucket created ✓"
    else
        log_info "S3 bucket already exists ✓"
    fi
    
    # Create DynamoDB table
    if ! aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &> /dev/null; then
        log_info "Creating DynamoDB table: $TABLE_NAME"
        aws dynamodb create-table \
            --table-name "$TABLE_NAME" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION"
        
        log_info "DynamoDB table created ✓"
    else
        log_info "DynamoDB table already exists ✓"
    fi
}

update_terraform_config() {
    log_info "Updating Terraform configuration..."
    
    # Update backend configuration
    sed -i.bak "s/your-terraform-state-bucket/$BUCKET_NAME/g" terraform/main.tf
    sed -i.bak "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" terraform/main.tf
    
    log_info "Terraform config updated ✓"
}

deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    terraform init
    
    # Validate configuration
    terraform validate
    
    # Create workspace for environment
    terraform workspace new production 2>/dev/null || terraform workspace select production
    
    # Plan
    log_info "Creating Terraform plan..."
    terraform plan -out=tfplan
    
    # Ask for confirmation
    read -p "Apply Terraform plan? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_warn "Deployment cancelled"
        exit 0
    fi
    
    # Apply
    terraform apply tfplan
    
    # Get outputs
    EKS_CLUSTER_NAME=$(terraform output -raw eks_cluster_name)
    RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
    REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
    ECR_REPOSITORY=$(terraform output -raw ecr_repository_url)
    
    log_info "Infrastructure deployed ✓"
    
    cd ..
}

configure_kubectl() {
    log_info "Configuring kubectl for EKS..."
    
    aws eks update-kubeconfig \
        --region "$AWS_REGION" \
        --name "$EKS_CLUSTER_NAME"
    
    # Verify connection
    if kubectl cluster-info &> /dev/null; then
        log_info "kubectl configured ✓"
    else
        log_error "Failed to configure kubectl"
        exit 1
    fi
}

install_kubernetes_addons() {
    log_info "Installing Kubernetes addons..."
    
    # Install AWS Load Balancer Controller
    log_info "Installing AWS Load Balancer Controller..."
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    
    kubectl create namespace kube-system 2>/dev/null || true
    
    helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName="$EKS_CLUSTER_NAME" \
        --set serviceAccount.create=true \
        --set region="$AWS_REGION" \
        --set vpcId="$VPC_ID"
    
    # Install metrics-server
    log_info "Installing metrics-server..."
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
    
    # Install Prometheus + Grafana
    log_info "Installing Prometheus stack..."
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    kubectl create namespace monitoring 2>/dev/null || true
    
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        -n monitoring \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --set grafana.adminPassword="$GRAFANA_PASSWORD"
    
    # Install Fluent Bit for logging
    log_info "Installing Fluent Bit..."
    helm repo add fluent https://fluent.github.io/helm-charts
    helm repo update
    
    helm upgrade --install fluent-bit fluent/fluent-bit \
        -n kube-system \
        --set cloudWatch.enabled=true \
        --set cloudWatch.region="$AWS_REGION" \
        --set cloudWatch.logGroupName="/aws/eks/$EKS_CLUSTER_NAME"
    
    log_info "Kubernetes addons installed ✓"
}

build_and_push_image() {
    log_info "Building and pushing Docker image..."
    
    # Login to ECR
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_REPOSITORY"
    
    # Build image
    IMAGE_TAG="$(git rev-parse --short HEAD)"
    docker build -t "$ECR_REPOSITORY:$IMAGE_TAG" .
    docker tag "$ECR_REPOSITORY:$IMAGE_TAG" "$ECR_REPOSITORY:latest"
    
    # Push image
    docker push "$ECR_REPOSITORY:$IMAGE_TAG"
    docker push "$ECR_REPOSITORY:latest"
    
    log_info "Docker image pushed ✓"
}

create_kubernetes_secrets() {
    log_info "Creating Kubernetes secrets..."
    
    kubectl create namespace production 2>/dev/null || true
    
    # Get secrets from AWS Secrets Manager
    DJANGO_SECRET_KEY=$(aws secretsmanager get-secret-value \
        --secret-id "django-api/production/django-secret-key" \
        --query SecretString --output text)
    
    DB_URL=$(aws secretsmanager get-secret-value \
        --secret-id "django-api/production/database-url" \
        --query SecretString --output text | jq -r .url)
    
    REDIS_AUTH_TOKEN=$(aws secretsmanager get-secret-value \
        --secret-id "django-api/production/redis-auth-token" \
        --query SecretString --output text)
    
    # Create Kubernetes secret
    kubectl create secret generic django-secrets \
        --from-literal=DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
        --from-literal=DATABASE_URL="$DB_URL" \
        --from-literal=REDIS_ENDPOINT="$REDIS_ENDPOINT" \
        --from-literal=REDIS_AUTH_TOKEN="$REDIS_AUTH_TOKEN" \
        -n production \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "Kubernetes secrets created ✓"
}

deploy_application() {
    log_info "Deploying Django application..."
    
    # Update Helm values
    sed -i.bak "s|ACCOUNT_ID|$AWS_ACCOUNT_ID|g" helm/django-api/values-production.yaml
    sed -i.bak "s|latest|$IMAGE_TAG|g" helm/django-api/values-production.yaml
    
    # Deploy with Helm
    helm upgrade --install django-api ./helm/django-api \
        --namespace production \
        --create-namespace \
        --values helm/django-api/values-production.yaml \
        --wait \
        --timeout 10m
    
    log_info "Application deployed ✓"
}

run_migrations() {
    log_info "Running database migrations..."
    
    kubectl run django-migrate \
        --image="$ECR_REPOSITORY:$IMAGE_TAG" \
        --restart=Never \
        --namespace=production \
        --command -- python manage.py migrate --noinput
    
    # Wait for completion
    kubectl wait --for=condition=complete pod/django-migrate -n production --timeout=5m
    
    # Get logs
    kubectl logs django-migrate -n production
    
    # Cleanup
    kubectl delete pod django-migrate -n production
    
    log_info "Migrations completed ✓"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pod status
    kubectl get pods -n production -l app=django-api
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod \
        -l app=django-api \
        -n production \
        --timeout=5m
    
    # Get service endpoint
    ENDPOINT=$(kubectl get ingress django-api-ingress \
        -n production \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    log_info "Endpoint: https://$ENDPOINT"
    
    # Test health endpoint
    sleep 30  # Wait for ALB to be ready
    
    if curl -f "https://$ENDPOINT/health/" &> /dev/null; then
        log_info "Health check passed ✓"
    else
        log_warn "Health check failed - application may still be starting"
    fi
}

print_summary() {
    log_info "========================================="
    log_info "Deployment Summary"
    log_info "========================================="
    log_info "EKS Cluster: $EKS_CLUSTER_NAME"
    log_info "ECR Repository: $ECR_REPOSITORY"
    log_info "Application Endpoint: https://$ENDPOINT"
    log_info ""
    log_info "Useful commands:"
    log_info "  - View logs: kubectl logs -f -l app=django-api -n production"
    log_info "  - Scale up: kubectl scale deployment django-api --replicas=5 -n production"
    log_info "  - View metrics: kubectl top pods -n production"
    log_info "  - Access Grafana: kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring"
    log_info "========================================="
}

# Main execution
main() {
    log_info "Starting Django on EKS deployment..."
    
    check_dependencies
    configure_aws
    create_terraform_backend
    update_terraform_config
    deploy_infrastructure
    configure_kubectl
    install_kubernetes_addons
    build_and_push_image
    create_kubernetes_secrets
    deploy_application
    run_migrations
    verify_deployment
    print_summary
    
    log_info "Deployment completed successfully! 🎉"
}

# Run main function
main "$@"
