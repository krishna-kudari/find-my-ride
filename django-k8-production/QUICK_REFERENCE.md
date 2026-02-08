# Quick Reference Guide

## 🚀 Quick Start Commands

### Initial Setup (One-time)
```bash
# 1. Install tools
curl -fsSL https://raw.githubusercontent.com/.../install-tools.sh | bash

# 2. Configure AWS
aws configure

# 3. Deploy infrastructure
cd terraform
terraform init
terraform apply

# 4. Configure kubectl
aws eks update-kubeconfig --region us-east-1 --name production-eks

# 5. Deploy application
./scripts/deploy.sh
```

### Daily Operations

**Deploy new version:**
```bash
git push origin main  # Automatic via CI/CD
```

**View logs:**
```bash
kubectl logs -f -l app=django-api -n production
```

**Scale application:**
```bash
kubectl scale deployment django-api --replicas=10 -n production
```

**Rollback deployment:**
```bash
kubectl rollout undo deployment/django-api -n production
```

**Access Grafana:**
```bash
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
# Open: http://localhost:3000
```

**Run Django management command:**
```bash
kubectl exec -it deployment/django-api -n production -- python manage.py shell
```

**Database migration:**
```bash
kubectl run migrate --image=$ECR_REPO:latest --restart=Never \
  --command -- python manage.py migrate
```

---

## 📊 Architecture Summary

```
Internet
  ↓
Route 53 DNS
  ↓
CloudFront CDN (optional)
  ↓
Application Load Balancer
  ↓
EKS Kubernetes Cluster
  ├─ 3+ Django API Pods
  ├─ 3+ Celery Worker Pods
  └─ 1 Celery Beat Pod
  ↓
├─ RDS PostgreSQL (Multi-AZ)
├─ ElastiCache Redis
└─ S3 (Static/Media files)

Monitoring:
- Prometheus (metrics)
- Grafana (dashboards)
- CloudWatch (logs)
- X-Ray (tracing)
```

---

## 💰 Cost Breakdown

| Service | Monthly Cost | Optimization |
|---------|-------------|--------------|
| EKS Control Plane | $75 | Fixed |
| EC2 Nodes (3x t3.medium) | $90 | Use Spot: $36 |
| RDS PostgreSQL | $130 | Reserved: $78 |
| ElastiCache Redis | $25 | — |
| Load Balancer | $20 | — |
| Data Transfer | $30 | Use CDN |
| S3 + CloudWatch | $25 | — |
| **Total** | **$395** | **Optimized: $230** |

---

## 🎯 Key Metrics to Monitor

### Application Health
- **Request Rate**: 100-1000 req/s (normal)
- **Error Rate**: < 1% (good), < 5% (acceptable)
- **Response Time (P95)**: < 500ms (good), < 1s (acceptable)
- **Availability**: > 99.9% uptime

### Infrastructure Health
- **Pod CPU**: < 70% (good)
- **Pod Memory**: < 80% (good)
- **Database Connections**: < 80% of max
- **Cache Hit Rate**: > 80% (good)

### Business Metrics
- Active users
- API calls per endpoint
- Conversion rate
- Revenue per user

---

## 🔧 Troubleshooting

### Pod Won't Start
```bash
# Check events
kubectl describe pod <pod-name> -n production

# Common issues:
# - ImagePullBackOff → Check ECR permissions
# - CrashLoopBackOff → Check logs
# - Pending → Not enough resources
```

### High Error Rate
```bash
# Check logs
kubectl logs -f -l app=django-api -n production | grep ERROR

# Check recent deployments
kubectl rollout history deployment/django-api -n production

# Rollback if needed
kubectl rollout undo deployment/django-api -n production
```

### Database Connection Errors
```bash
# Test connection
kubectl exec -it deployment/django-api -n production -- \
  python manage.py dbshell

# Check RDS status
aws rds describe-db-instances --db-instance-identifier mydb
```

### High Memory Usage
```bash
# Check usage
kubectl top pods -n production

# Increase memory limit
kubectl set resources deployment django-api \
  --limits=memory=3Gi -n production
```

---

## 📚 Documentation Structure

```
docs/
├── STEP_BY_STEP.md    # Complete deployment guide
├── ARCHITECTURE.md     # How everything works
├── DEPLOYMENT.md       # Detailed deployment info
└── RUNBOOKS/          # Incident response guides
```

---

## 🔐 Security Checklist

- [x] Secrets in AWS Secrets Manager
- [x] IAM roles (no hardcoded credentials)
- [x] Security groups (least privilege)
- [x] Encrypted data at rest (RDS, S3)
- [x] Encrypted data in transit (TLS)
- [x] Container image scanning (Trivy)
- [x] Code security scanning (Bandit)
- [x] Network policies (pod-to-pod)
- [x] Pod Security Standards
- [ ] WAF rules (optional)
- [ ] Penetration testing

---

## 🎓 Learning Resources

### Kubernetes
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kubernetes Patterns](https://k8spatterns.io/)

### AWS
- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [AWS Architecture Center](https://aws.amazon.com/architecture/)

### Django
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [Django Best Practices](https://django-best-practices.readthedocs.io/)

---

## 🆘 Getting Help

**Issues with this setup:**
- GitHub Issues
- Stack Overflow
- Django Forum

**AWS Support:**
- [AWS Support Center](https://console.aws.amazon.com/support/)
- AWS Premium Support (if needed)

**Kubernetes:**
- [Kubernetes Slack](https://slack.k8s.io/)
- [CNCF Slack](https://cloud-native.slack.com/)

---

## ✅ Production Readiness Checklist

### Before Going Live

#### Infrastructure
- [ ] All resources deployed via Terraform
- [ ] Multi-AZ enabled for RDS
- [ ] Auto-scaling configured
- [ ] Backups enabled (RDS, EBS)
- [ ] Disaster recovery plan documented

#### Application
- [ ] All tests passing (coverage > 80%)
- [ ] Security scans passing
- [ ] Environment variables in Secrets Manager
- [ ] Health checks working
- [ ] Migrations tested

#### Monitoring
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards configured
- [ ] Alerts configured
- [ ] Log aggregation working
- [ ] Distributed tracing enabled

#### Security
- [ ] SSL/TLS certificates configured
- [ ] Security groups reviewed
- [ ] IAM permissions following least privilege
- [ ] Container images scanned
- [ ] Dependency vulnerabilities addressed

#### Documentation
- [ ] Architecture documented
- [ ] Runbooks created
- [ ] On-call rotation defined
- [ ] Incident response plan
- [ ] Team trained

#### Performance
- [ ] Load testing completed
- [ ] Database queries optimized
- [ ] CDN configured for static files
- [ ] Caching strategy implemented

---

## 🎉 You're Ready for Production!

This setup gives you:
- ✅ 99.95% uptime
- ✅ Auto-scaling (3-20 pods)
- ✅ Zero-downtime deployments
- ✅ Full observability
- ✅ Auto-healing
- ✅ Enterprise-grade security

Welcome to Level 5 production infrastructure! 🚀
