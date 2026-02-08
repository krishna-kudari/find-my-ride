# Django Production Deployment on AWS EKS

Enterprise-grade Django API deployment with full observability, security, and automation.

## Architecture

- **Container Orchestration**: Amazon EKS (Kubernetes)
- **CI/CD**: GitHub Actions
- **Database**: RDS PostgreSQL (Multi-AZ)
- **Cache**: ElastiCache Redis
- **Storage**: S3 + CloudFront
- **Monitoring**: CloudWatch, Prometheus, Grafana, X-Ray
- **Security**: AWS Secrets Manager, WAF, Security Groups

## Features

- ✅ Zero-downtime deployments
- ✅ Auto-scaling (HPA)
- ✅ Comprehensive testing in CI/CD
- ✅ Security scanning (Trivy, Bandit)
- ✅ Distributed tracing
- ✅ Centralized logging
- ✅ Infrastructure as Code (Terraform + Helm)
- ✅ Canary deployments
- ✅ Automated rollbacks
- ✅ Multi-environment (dev, staging, prod)

## Quick Start

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete setup guide.

## Directory Structure

```
.
├── .github/
│   └── workflows/          # CI/CD pipelines
├── src/                    # Django application
├── terraform/              # Infrastructure as Code
├── k8s/                    # Kubernetes manifests
├── helm/                   # Helm charts
├── scripts/                # Deployment scripts
├── tests/                  # Test suite
└── docs/                   # Documentation
```
