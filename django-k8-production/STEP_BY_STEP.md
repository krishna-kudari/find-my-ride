# Step-by-Step Production Deployment Guide

## Overview

This guide will take you from your current setup (EC2 + git pull) to a production-grade Kubernetes deployment on AWS EKS with full observability, security, and automation.

**Estimated Time:** 4-6 hours for first-time setup
**Cost:** ~$400-500/month for production setup

---

## Phase 0: Prerequisites (30 minutes)

### 1. Create AWS Account
If you don't have one:
- Go to aws.amazon.com
- Sign up for new account
- Add payment method

### 2. Install Required Tools

**macOS:**
```bash
# Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install tools
brew install awscli kubectl helm terraform docker
```

**Linux (Ubuntu/Debian):**
```bash
# Run the installation script
curl -fsSL https://raw.githubusercontent.com/yourusername/django-k8s-production/main/scripts/install-tools.sh | bash
```

**Windows:**
- Install WSL2
- Follow Linux instructions

### 3. Verify Installations

```bash
# Check versions
aws --version        # Should be 2.x
kubectl version --client
helm version
terraform --version  # Should be 1.6+
docker --version
```

### 4. Configure AWS CLI

```bash
aws configure

# Enter your credentials:
AWS Access Key ID: [Your access key]
AWS Secret Access Key: [Your secret key]
Default region name: us-east-1
Default output format: json
```

**Get AWS credentials:**
1. Log into AWS Console
2. Go to IAM → Users → Your User
3. Security Credentials → Create Access Key
4. Download and save credentials

### 5. Set Up GitHub Repository

```bash
# Clone this repository
git clone https://github.com/yourusername/django-k8s-production
cd django-k8s-production

# Or start from your existing Django project
cd your-django-project

# Copy the deployment files
# ... (copy terraform/, k8s/, helm/, .github/ directories)
```

---

## Phase 1: Containerize Your Application (1 hour)

### Understanding: Why Containers?

**Current State (EC2 + git pull):**
```
Your EC2 server:
- Ubuntu 22.04
- Python 3.11 installed globally
- pip packages installed globally
- PostgreSQL running on same server
- nginx + gunicorn configured manually
- .env file with secrets

Problems:
❌ Can't easily scale to multiple servers
❌ Hard to recreate exact environment
❌ Manual configuration drift
❌ Downtime during deployments
```

**Container State:**
```
Docker container:
- Your app + Python + all dependencies
- Exact same environment everywhere
- Immutable (can't change once built)
- Can run 100 copies easily

Benefits:
✅ Scale to 100s of servers
✅ "Works on my machine" = "Works in production"
✅ Zero-downtime deployments
✅ Auto-healing if crashes
```

### Step 1: Review Dockerfile

Open `Dockerfile` in this repo and understand each line:

```dockerfile
# Stage 1: Build dependencies (big image, ~1GB)
FROM python:3.11-slim as builder
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime (small image, ~400MB)
FROM python:3.11-slim
COPY --from=builder /wheels /wheels  # Copy only built wheels
RUN pip install /wheels/*
COPY . .
CMD ["gunicorn", "config.wsgi:application", ...]
```

**Why multi-stage?**
- Stage 1 needs build tools (gcc, etc.) - 1.2GB
- Stage 2 only needs runtime - 400MB
- 70% size reduction = faster deploys

### Step 2: Prepare Your Application

**Create requirements files:**

```bash
# requirements/base.txt (production dependencies)
Django==4.2.7
psycopg2-binary==2.9.9
gunicorn==21.2.0
django-redis==5.4.0
celery==5.3.4
boto3==1.29.7
django-storages==1.14.2
django-prometheus==2.3.1
aws-xray-sdk==2.12.1
python-json-logger==2.0.7

# requirements/dev.txt (development dependencies)
-r base.txt
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
black==23.12.0
flake8==6.1.0
mypy==1.7.1
bandit==1.7.5
```

### Step 3: Add Health Check Endpoints

Copy `/src/apps/core/views/health.py` from this repo to your project.

**Add to urls.py:**
```python
from apps.core.views import health

urlpatterns = [
    path('health/', health.health_check, name='health'),
    path('ready/', health.readiness_check, name='ready'),
    path('status/', health.status, name='status'),
    path('metrics', health.metrics, name='metrics'),
]
```

**Why needed:**
- `/health/` - Kubernetes checks if pod is alive
- `/ready/` - Kubernetes checks if pod can serve traffic
- `/metrics` - Prometheus scrapes performance data

### Step 4: Test Locally with Docker

```bash
# Build image
docker build -t django-api:local .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://localhost:6379/0 \
  django-api:local

# Test health endpoint
curl http://localhost:8000/health/
# Should return: {"status": "healthy", "service": "django-api"}
```

### Step 5: Test Full Stack with Docker Compose

```bash
# Start all services (Django, PostgreSQL, Redis, Celery)
docker-compose up

# In another terminal, run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Visit http://localhost:8000
```

**Understanding docker-compose.yml:**
```yaml
services:
  db:          # PostgreSQL container
  redis:       # Redis container
  web:         # Django API container
  celery:      # Celery worker container
  celery-beat: # Celery scheduler container
```

All containers can talk to each other by service name (e.g., `db:5432`).

---

## Phase 2: Infrastructure Setup with Terraform (1-2 hours)

### Understanding: What is Terraform?

**Without Terraform (Manual AWS Console):**
```
Day 1: Click through AWS console
  - Create VPC
  - Create subnets
  - Create EKS cluster
  - Create RDS database
  - Click, click, click... (30 minutes)

Day 30: Need to recreate in another region
  - Uh... what did I click?
  - Forgot security group rules
  - Database settings?
  - Start over... (2 hours, might miss something)
```

**With Terraform:**
```bash
# Day 1:
terraform apply  # Creates everything in 15 minutes

# Day 30:
terraform apply  # Recreates EXACTLY the same in 15 minutes

# Day 60:
terraform destroy  # Deletes everything cleanly
```

### What Terraform Will Create

```
AWS Resources Created:
├── VPC (Virtual Private Cloud)
│   ├── 3 Public Subnets (for Load Balancers)
│   ├── 3 Private Subnets (for EKS pods)
│   ├── 3 Database Subnets (for RDS)
│   ├── Internet Gateway
│   └── 3 NAT Gateways (one per AZ)
│
├── EKS Cluster
│   ├── Control Plane (managed by AWS)
│   ├── Node Group (3 t3.medium EC2s)
│   └── Spot Node Group (2 t3.medium Spots)
│
├── RDS PostgreSQL
│   ├── Primary Instance (Multi-AZ)
│   ├── Standby Instance (auto-failover)
│   └── Automated backups
│
├── ElastiCache Redis
│   ├── Primary Node
│   └── Replica Node (if production)
│
├── S3 Buckets
│   ├── Static files bucket
│   ├── Media files bucket
│   └── Terraform state bucket
│
├── ECR Repository (Docker images)
│
├── Secrets Manager
│   ├── Django SECRET_KEY
│   ├── Database credentials
│   └── Redis auth token
│
└── IAM Roles & Policies

Total Cost: ~$400/month
```

### Step 1: Review Terraform Code

Open `terraform/main.tf` and understand the structure:

```hcl
# Define what you want
resource "aws_eks_cluster" "main" {
  name    = "my-cluster"
  version = "1.28"
  # ...
}

# Terraform will:
1. Check what exists in AWS
2. Calculate difference
3. Create/update/delete resources
4. Save state
```

### Step 2: Customize Variables

Edit `terraform/terraform.tfvars`:

```hcl
aws_region      = "us-east-1"
environment     = "production"
project_name    = "myapp"

# VPC
vpc_cidr = "10.0.0.0/16"

# RDS
rds_instance_class       = "db.t3.medium"  # ~$130/month
rds_allocated_storage    = 20              # GB
rds_max_allocated_storage = 100            # Auto-scales to this

# Redis
redis_node_type = "cache.t3.micro"  # ~$25/month

# EKS
eks_node_instance_type = "t3.medium"  # ~$30/month per node
eks_node_count_min     = 2
eks_node_count_max     = 10
```

**Cost breakdown:**
- EKS Control Plane: $75/month
- 3x t3.medium nodes: $90/month
- RDS Multi-AZ: $130/month
- Redis: $25/month
- Load Balancer: $20/month
- Data transfer: ~$30/month
- **Total: ~$370/month**

### Step 3: Initialize Terraform

```bash
cd terraform

# Initialize (downloads providers)
terraform init

# This creates:
# .terraform/ directory with provider plugins
# .terraform.lock.hcl (dependency lock file)
```

### Step 4: Create Terraform Backend

**Why needed?**
- Stores state file in S3 (not locally)
- Enables team collaboration
- State locking prevents conflicts

```bash
# Run backend setup
./scripts/setup-terraform-backend.sh

# This creates:
# - S3 bucket: terraform-state-{your-account-id}
# - DynamoDB table: terraform-state-lock
```

### Step 5: Plan Infrastructure

```bash
# See what will be created
terraform plan

# Output shows:
# + resources to create (green)
# - resources to destroy (red)
# ~ resources to modify (yellow)

# Should see ~50 resources to create
```

**Read the plan carefully!**

Example:
```
# aws_eks_cluster.main will be created
+ resource "aws_eks_cluster" "main" {
    + name    = "myapp-production-eks"
    + version = "1.28"
    # ...
  }

# aws_rds_cluster.main will be created
+ resource "aws_rds_cluster" "main" {
    + engine  = "postgres"
    + version = "15.4"
    # ...
  }
```

### Step 6: Apply Infrastructure

```bash
# Create everything
terraform apply

# Type 'yes' when prompted

# This takes 15-20 minutes
# Watch the progress:
# - VPC created (1 min)
# - EKS cluster created (10-15 min) ← slowest
# - RDS created (5 min)
# - Other resources (2-3 min)
```

**What happens internally:**
```
1. Terraform calls AWS APIs
2. AWS creates resources
3. Terraform waits for resources to be ready
4. Terraform saves state to S3
5. Terraform outputs important values
```

### Step 7: Save Terraform Outputs

```bash
# Get important values
terraform output

# Save these:
eks_cluster_name = "myapp-production-eks"
rds_endpoint     = "mydb.abc123.us-east-1.rds.amazonaws.com"
redis_endpoint   = "myredis.abc123.use1.cache.amazonaws.com"
ecr_repository   = "123456789.dkr.ecr.us-east-1.amazonaws.com/myapp"

# Export as environment variables
export EKS_CLUSTER_NAME=$(terraform output -raw eks_cluster_name)
export ECR_REPOSITORY=$(terraform output -raw ecr_repository_url)
```

---

## Phase 3: Configure Kubernetes (1 hour)

### Understanding: EKS vs Your Current Setup

**Current (Single EC2):**
```
Your EC2 server:
- Runs nginx
- Runs gunicorn (1 process)
- If it crashes: Downtime
- If traffic spikes: Overloaded
- Deploy: SSH and restart
```

**EKS (Kubernetes):**
```
3 Worker Nodes (EC2 instances):
  Node 1: Running 5 Django pods
  Node 2: Running 5 Django pods  
  Node 3: Running 5 Django pods

If one crashes:
- Kubernetes auto-restarts it (15 seconds)
- Traffic routes to other 14 pods
- No downtime

If traffic spikes:
- Kubernetes auto-adds more pods (2 minutes)
- Can scale to 100 pods

Deploy:
- Push new container image
- Kubernetes rolls out gradually
- Zero downtime
```

### Step 1: Configure kubectl

```bash
# Connect kubectl to your EKS cluster
aws eks update-kubeconfig \
  --region us-east-1 \
  --name $EKS_CLUSTER_NAME

# Verify connection
kubectl get nodes

# Should show:
NAME                          STATUS   ROLES    AGE
ip-10-0-1-123.ec2.internal    Ready    <none>   5m
ip-10-0-2-456.ec2.internal    Ready    <none>   5m
ip-10-0-3-789.ec2.internal    Ready    <none>   5m
```

### Step 2: Install Kubernetes Addons

**These are system components that run on your cluster.**

```bash
# 1. AWS Load Balancer Controller
# Creates AWS ALB when you create Ingress
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$EKS_CLUSTER_NAME

# 2. Metrics Server
# Enables 'kubectl top pods' command
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 3. Prometheus + Grafana (Monitoring)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace

# 4. Fluent Bit (Log shipping to CloudWatch)
helm repo add fluent https://fluent.github.io/helm-charts
helm install fluent-bit fluent/fluent-bit \
  -n kube-system \
  --set cloudWatch.enabled=true \
  --set cloudWatch.region=us-east-1 \
  --set cloudWatch.logGroupName=/aws/eks/$EKS_CLUSTER_NAME
```

**What each does:**

| Addon | Purpose | Example |
|-------|---------|---------|
| Load Balancer Controller | Creates AWS ALB | When you deploy app, gets public URL |
| Metrics Server | Resource monitoring | `kubectl top pods` shows CPU/memory |
| Prometheus | Metrics collection | Collects request rate, errors, latency |
| Grafana | Metrics visualization | Dashboards showing app performance |
| Fluent Bit | Log shipping | All logs go to CloudWatch |

### Step 3: Create Kubernetes Secrets

**Why not use .env files?**
- .env files would be in container image (visible to anyone)
- Secrets Manager is encrypted
- Can rotate secrets without rebuilding image

```bash
# Get secrets from AWS Secrets Manager
DJANGO_SECRET_KEY=$(aws secretsmanager get-secret-value \
  --secret-id myapp/production/django-secret-key \
  --query SecretString --output text)

DB_URL=$(aws secretsmanager get-secret-value \
  --secret-id myapp/production/database-url \
  --query SecretString --output text | jq -r .url)

# Create Kubernetes secret
kubectl create secret generic django-secrets \
  --from-literal=DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
  --from-literal=DATABASE_URL="$DB_URL" \
  -n production

# Verify
kubectl get secrets -n production
```

---

## Phase 4: Deploy Application (30 minutes)

### Understanding: Helm Charts

**Without Helm:**
```yaml
# You need to create:
deployment.yaml (100 lines)
service.yaml (20 lines)
ingress.yaml (30 lines)
configmap.yaml (20 lines)
hpa.yaml (15 lines)
pdb.yaml (10 lines)
... 10+ files
```

**With Helm:**
```bash
helm install myapp ./helm/django-api
# One command deploys everything
```

### Step 1: Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_REPOSITORY

# Build image
IMAGE_TAG=$(git rev-parse --short HEAD)
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .
docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_REPOSITORY:latest

# Push to ECR
docker push $ECR_REPOSITORY:$IMAGE_TAG
docker push $ECR_REPOSITORY:latest

# Verify
aws ecr describe-images --repository-name myapp
```

**What's in ECR now:**
```
Your private Docker registry:
├── myapp:a1b2c3d (this commit)
├── myapp:latest (always points to newest)
└── ... (previous versions)
```

### Step 2: Customize Helm Values

Edit `helm/django-api/values-production.yaml`:

```yaml
image:
  repository: 123456789.dkr.ecr.us-east-1.amazonaws.com/myapp
  tag: latest

replicaCount: 3  # 3 Django pods

resources:
  limits:
    cpu: 1000m     # 1 CPU
    memory: 2Gi    # 2GB RAM
  requests:
    cpu: 500m      # Reserve 0.5 CPU
    memory: 1Gi    # Reserve 1GB RAM

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70  # Scale up when CPU > 70%

ingress:
  enabled: true
  hosts:
    - host: api.yourdomain.com
```

### Step 3: Deploy with Helm

```bash
# Deploy application
helm upgrade --install django-api ./helm/django-api \
  --namespace production \
  --create-namespace \
  --values helm/django-api/values-production.yaml \
  --wait

# Watch deployment progress
kubectl get pods -n production -w

# Should see pods starting:
NAME                         READY   STATUS    RESTARTS   AGE
django-api-7d9f8c-abc12     0/1     Init:0/1  0          5s
django-api-7d9f8c-abc12     0/1     Running   0          10s
django-api-7d9f8c-abc12     1/1     Running   0          30s
```

**What Helm created:**

```bash
# Check what was created
kubectl get all -n production

# Output:
NAME                             READY   STATUS    RESTARTS   AGE
pod/django-api-abc123            1/1     Running   0          2m
pod/django-api-def456            1/1     Running   0          2m
pod/django-api-ghi789            1/1     Running   0          2m

NAME                    TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
service/django-api      ClusterIP   10.100.50.123   <none>        80/TCP     2m

NAME                         READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/django-api   3/3     3            3           2m

NAME                                   DESIRED   CURRENT   READY   AGE
replicaset.apps/django-api-7d9f8c     3         3         3       2m
```

### Step 4: Run Database Migrations

```bash
# Run migrations as a one-time job
kubectl run django-migrate \
  --image=$ECR_REPOSITORY:latest \
  --restart=Never \
  --namespace=production \
  --command -- python manage.py migrate --noinput

# Watch logs
kubectl logs -f django-migrate -n production

# Cleanup
kubectl delete pod django-migrate -n production
```

### Step 5: Verify Deployment

```bash
# Check pod status
kubectl get pods -n production

# Check logs
kubectl logs -f deployment/django-api -n production

# Get application URL
kubectl get ingress -n production

# Output:
NAME         HOSTS                ADDRESS                     PORTS
django-api   api.yourdomain.com   abc123.elb.amazonaws.com    80, 443

# Test health endpoint
ENDPOINT=$(kubectl get ingress django-api-ingress -n production -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
curl https://$ENDPOINT/health/
```

---

## Phase 5: Set Up Monitoring (30 minutes)

### Understanding: The Three Pillars of Observability

```
1. LOGS (What happened?)
   "User 123 logged in at 10:00 AM"
   "Error: Database connection failed"

2. METRICS (How much/many?)
   Request rate: 100 req/s
   Error rate: 2%
   Response time: 200ms

3. TRACES (Where is time spent?)
   Request took 1.2s:
   ├─ Django view: 0.05s
   ├─ Database query: 0.8s ← SLOW!
   ├─ Redis get: 0.02s
   └─ Render: 0.03s
```

### Step 1: Access Grafana Dashboard

```bash
# Get Grafana password
kubectl get secret prometheus-grafana \
  -n monitoring \
  -o jsonpath="{.data.admin-password}" | base64 --decode

# Port forward to access locally
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring

# Open browser: http://localhost:3000
# Username: admin
# Password: (from command above)
```

### Step 2: Import Django Dashboard

1. In Grafana, click "+" → Import
2. Upload `k8s/monitoring/grafana-dashboard.json`
3. Select Prometheus as data source
4. Click "Import"

**You should now see:**
- Request rate graph
- Error rate graph
- Response time (P50, P95, P99)
- CPU/Memory usage
- Database connections
- Cache hit rate

### Step 3: Set Up Alerts

```bash
# Deploy Prometheus rules
kubectl apply -f k8s/monitoring/servicemonitor.yaml

# Verify alerts
kubectl get prometheusrule -n monitoring
```

**Alerts configured:**
- High error rate (>5% for 5 min) → Critical
- High response time (P95 > 1s for 10 min) → Warning
- Pod down (any pod down for 1 min) → Critical
- High memory usage (>85% for 5 min) → Warning

### Step 4: Configure Slack Notifications

1. Create Slack webhook:
   - Go to https://api.slack.com/apps
   - Create new app
   - Add "Incoming Webhooks"
   - Copy webhook URL

2. Add to AlertManager:
```bash
kubectl create secret generic alertmanager-slack \
  --from-literal=url='https://hooks.slack.com/services/YOUR/WEBHOOK/URL' \
  -n monitoring
```

3. Configure AlertManager:
```yaml
# Edit AlertManager config
kubectl edit configmap alertmanager-prometheus-kube-prometheus-alertmanager -n monitoring

# Add:
receivers:
- name: slack
  slack_configs:
  - api_url: <slack_webhook_url>
    channel: '#alerts'
    title: 'Alert: {{ .CommonLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### Step 5: View Logs in CloudWatch

```bash
# Logs are automatically shipped to CloudWatch

# View in AWS Console:
1. Go to CloudWatch → Log groups
2. Find: /aws/eks/production-eks/django-api
3. Click on log stream
4. Search logs

# Or use CLI:
aws logs tail /aws/eks/production-eks/django-api --follow
```

**CloudWatch Insights queries:**

```sql
-- Find all errors in last hour
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100

-- Find slow requests
fields @timestamp, request_time, path
| filter request_time > 1000
| sort request_time desc
```

---

## Phase 6: Set Up CI/CD (30 minutes)

### Understanding: What Happens on Every Git Push

```
1. Developer pushes code to GitHub
   ↓
2. GitHub Actions triggered
   ↓
3. Run tests (pytest)
   ├─ If tests fail → Stop here ❌
   └─ If tests pass → Continue ✓
   ↓
4. Run security scans
   ├─ Scan code (bandit)
   ├─ Scan dependencies (safety)
   └─ Scan Docker image (trivy)
   ↓
5. Build Docker image
   ↓
6. Push to ECR
   ↓
7. Update Kubernetes deployment
   ↓
8. Verify deployment
   ├─ Check pod status
   ├─ Test health endpoint
   └─ Run smoke tests
   ↓
9. Send Slack notification ✓

Total time: ~10 minutes
```

### Step 1: Add GitHub Secrets

Go to GitHub repo → Settings → Secrets and variables → Actions

Add these secrets:
```
AWS_ACCESS_KEY_ID: (Your AWS access key)
AWS_SECRET_ACCESS_KEY: (Your AWS secret key)
SLACK_WEBHOOK_URL: (Your Slack webhook)
```

### Step 2: Review CI/CD Workflow

Open `.github/workflows/ci-cd.yml` and understand the jobs:

```yaml
jobs:
  test:          # Run tests, linting, security scans
  build:         # Build and scan Docker image
  migrate:       # Run database migrations
  deploy:        # Deploy to Kubernetes
```

### Step 3: Test CI/CD

```bash
# Make a small change
echo "# Test CI/CD" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI/CD pipeline"
git push origin main

# Watch in GitHub:
# Go to Actions tab
# See workflow running
```

**Workflow progress:**
```
✓ Checkout code (10s)
✓ Run tests (2 min)
✓ Security scans (1 min)
✓ Build Docker image (3 min)
✓ Scan image (1 min)
✓ Push to ECR (1 min)
✓ Deploy to EKS (2 min)
✓ Verify deployment (30s)
Total: ~10 minutes
```

### Step 4: Verify Deployment

```bash
# Check if new version deployed
kubectl get pods -n production

# Check image version
kubectl describe pod django-api-xxx -n production | grep Image

# Should show new commit SHA
```

---

## Phase 7: Post-Deployment Operations

### Daily Operations

**View logs:**
```bash
# All pods
kubectl logs -f -l app=django-api -n production

# Specific pod
kubectl logs -f django-api-abc123 -n production

# Previous crashed pod
kubectl logs -f django-api-abc123 -n production --previous
```

**Scale application:**
```bash
# Scale up
kubectl scale deployment django-api --replicas=10 -n production

# Scale down
kubectl scale deployment django-api --replicas=3 -n production

# Auto-scaling is already enabled, so this happens automatically
```

**Deploy new version:**
```bash
# Just push to GitHub main branch
git push origin main

# Or manually:
kubectl set image deployment/django-api \
  django-api=$ECR_REPOSITORY:new-tag \
  -n production
```

**Rollback deployment:**
```bash
# Rollback to previous version
kubectl rollout undo deployment/django-api -n production

# Rollback to specific version
kubectl rollout history deployment/django-api -n production
kubectl rollout undo deployment/django-api --to-revision=2 -n production
```

**Check resource usage:**
```bash
# Pod CPU and memory
kubectl top pods -n production

# Node CPU and memory
kubectl top nodes
```

### Troubleshooting

**Pod won't start:**
```bash
# Check pod events
kubectl describe pod django-api-xxx -n production

# Common issues:
# - Image pull error → Check ECR permissions
# - CrashLoopBackOff → Check logs
# - Pending → Not enough resources
```

**High error rate alert:**
```bash
# Check logs for errors
kubectl logs -f -l app=django-api -n production | grep ERROR

# Check recent deployment
kubectl rollout history deployment/django-api -n production

# Rollback if needed
kubectl rollout undo deployment/django-api -n production
```

**Database connection errors:**
```bash
# Check database endpoint
echo $RDS_ENDPOINT

# Test connection from pod
kubectl exec -it django-api-xxx -n production -- \
  python manage.py dbshell

# Check RDS status in AWS Console
```

### Cost Optimization

**Monitor costs:**
```bash
# Use AWS Cost Explorer
# Filter by tag: Environment=production
```

**Optimization tips:**
1. Use Spot instances for Celery workers (60% savings)
2. Right-size instance types based on metrics
3. Enable S3 Intelligent-Tiering
4. Use RDS reserved instances (40% savings)
5. Set up auto-scaling to scale down at night

---

## Summary: What You've Achieved

### Before (EC2 + git pull)
```
Single EC2 server
- 1 application instance
- 95% uptime (if lucky)
- Manual deployments (downtime)
- SSH to check logs
- No monitoring
- Scale: Manual, slow
- Deploy: SSH and pray
Cost: ~$30/month
```

### After (EKS + Full Observability)
```
Production Kubernetes Cluster
- 3+ application instances (auto-scaling)
- 99.95% uptime
- Zero-downtime deployments
- Centralized logging (CloudWatch)
- Full metrics (Prometheus + Grafana)
- Auto-healing, auto-scaling
- Deploy: git push (10 min, automated)
Cost: ~$400/month
```

### Capabilities Unlocked

✅ **Scalability**: Handle 100x traffic automatically
✅ **Reliability**: 99.95% uptime, auto-healing
✅ **Observability**: Full visibility into performance
✅ **Security**: Encrypted secrets, security scanning
✅ **Automation**: Deploy 10x/day with confidence
✅ **Team Collaboration**: Multiple developers, no conflicts
✅ **Compliance**: Audit logs, encryption, backups

### Next Steps

1. **Add More Services**: Add frontend, admin panel
2. **Multi-Region**: Deploy to multiple AWS regions
3. **Advanced Monitoring**: Add Sentry, DataDog
4. **Service Mesh**: Add Istio for microservices
5. **GitOps**: Use ArgoCD for deployment
6. **Disaster Recovery**: Multi-region failover

---

## Getting Help

**Issues with this guide:**
- Create GitHub issue
- Check docs/ folder for detailed explanations

**AWS/Kubernetes questions:**
- AWS documentation: docs.aws.amazon.com
- Kubernetes docs: kubernetes.io/docs
- Stack Overflow

**Professional support:**
- AWS Support plans
- Hire DevOps consultant

---

## Conclusion

You now have a production-grade infrastructure that:
- Scales automatically
- Heals itself
- Has full observability
- Deploys automatically
- Costs ~$400/month

This is the same setup used by companies like:
- Airbnb (Kubernetes)
- Spotify (Kubernetes)
- Shopify (Kubernetes)

Welcome to Level 5! 🎉
