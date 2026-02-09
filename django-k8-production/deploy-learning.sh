#!/bin/bash
# Cost-Optimized Deployment Script for Learning
# This script deploys a minimal setup for testing/learning purposes

set -e

echo "🚀 Deploying Cost-Optimized Django K8s Setup for Learning"
echo "=========================================================="
echo ""
echo "⚠️  WARNING: This will create AWS resources that cost money."
echo "   Estimated cost: ~$5-15 for 2-3 days of testing"
echo "   Make sure to run 'terraform destroy' when done!"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled."
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Run 'aws configure' first."
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not installed. Please install Terraform first."
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not installed. Please install kubectl first."
    exit 1
fi

echo ""
echo "📋 Pre-deployment Checklist:"
echo "  ✅ AWS CLI configured"
echo "  ✅ Terraform installed"
echo "  ✅ kubectl installed"
echo ""

# Navigate to terraform directory (if it exists)
if [ -d "terraform" ]; then
    cd terraform
fi

echo "🔧 Initializing Terraform..."
terraform init

echo ""
echo "📊 Planning deployment (dry-run)..."
terraform plan -var-file=../terraform.tfvars.learning

echo ""
read -p "Apply these changes? (yes/no): " apply_confirm

if [ "$apply_confirm" != "yes" ]; then
    echo "Deployment cancelled."
    exit 1
fi

echo ""
echo "🚀 Deploying infrastructure..."
terraform apply -var-file=../terraform.tfvars.learning -auto-approve

echo ""
echo "✅ Infrastructure deployed!"
echo ""
echo "📝 Next Steps:"
echo "  1. Configure kubectl:"
echo "     aws eks update-kubeconfig --region us-east-1 --name django-api-dev-eks"
echo ""
echo "  2. Deploy Django application (see DEPLOYMENT.md)"
echo ""
echo "  3. When done testing, destroy everything:"
echo "     terraform destroy -var-file=../terraform.tfvars.learning"
echo ""
echo "💰 Remember to destroy resources when done to avoid charges!"
echo ""
