# Complete Production Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Local Setup & Containerization](#phase-1-local-setup--containerization)
3. [Phase 2: Infrastructure Setup (Terraform)](#phase-2-infrastructure-setup-terraform)
4. [Phase 3: Kubernetes Configuration](#phase-3-kubernetes-configuration)
5. [Phase 4: CI/CD Pipeline](#phase-4-cicd-pipeline)
6. [Phase 5: Observability Stack](#phase-5-observability-stack)
7. [Phase 6: Production Deployment](#phase-6-production-deployment)
8. [Phase 7: Monitoring & Operations](#phase-7-monitoring--operations)

---

## Prerequisites

### Tools to Install

```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Terraform
wget https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip
unzip terraform_1.7.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# eksctl (EKS cluster management)
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### AWS Account Setup

1. Create AWS account
2. Create IAM user with admin access (for learning; restrict in production)
3. Configure AWS CLI:

```bash
aws configure
# AWS Access Key ID: YOUR_KEY
# AWS Secret Access Key: YOUR_SECRET
# Default region: us-east-1
# Default output format: json
```

### Domain Setup

1. Register domain or use existing
2. Create Route53 hosted zone
3. Update nameservers at domain registrar

---

## Phase 1: Local Setup & Containerization

### Why Containerization?

**Before (Your Current Setup):**
- Server has Python, dependencies installed globally
- Hard to replicate exact environment
- "Works on my machine" problems
- Difficult to scale

**After (Containers):**
- Exact same environment everywhere
- Easy to scale horizontally
- Version controlled
- Immutable deployments

### Step 1.1: Optimize Django Project Structure

**Create Multi-Stage Dockerfile** (reduces image size 60-70%)

Why multi-stage?
- Stage 1: Build dependencies (large)
- Stage 2: Copy only runtime needs (small)
- Result: 1.5GB → 400MB image

### Step 1.2: Docker Compose for Local Development

Why Docker Compose locally?
- Matches production environment
- Easy onboarding for new developers
- Test with real PostgreSQL/Redis
- No "works locally but not in prod"

### Step 1.3: Health Checks

Why critical?
- Kubernetes needs to know when pod is ready
- Load balancer needs to know healthy instances
- Auto-restart unhealthy containers

---

## Phase 2: Infrastructure Setup (Terraform)

### Why Terraform?

**Before (Manual AWS Console):**
- Click through console
- Forget what you created
- Can't recreate if deleted
- No version control
- Team can't collaborate

**After (Infrastructure as Code):**
- Everything in code
- Version controlled
- Repeatable
- Auditable
- Can recreate entire infra in minutes

### What Terraform Will Create

```
VPC
├── 3 Public Subnets (across 3 AZs)
├── 3 Private Subnets (for EKS)
├── NAT Gateways (for internet access from private)
└── Internet Gateway

EKS Cluster
├── Control Plane (managed by AWS)
├── Node Groups (3 nodes minimum)
└── IRSA (IAM Roles for Service Accounts)

RDS PostgreSQL
├── Multi-AZ (auto-failover)
├── Automated backups
├── Read replicas (optional)
└── Encryption at rest

ElastiCache Redis
├── Cluster mode enabled
└── Multi-AZ

S3 Buckets
├── Static files
├── Media files
└── Backups

Security Groups
├── EKS nodes
├── RDS
├── Redis
└── ALB

IAM Roles
├── EKS cluster role
├── Node group role
├── Pod execution roles
└── CI/CD roles
```

### How Terraform Works Internally

```
1. You write: main.tf (desired state)
2. Terraform reads: AWS current state
3. Terraform calculates: Difference (plan)
4. You approve: terraform apply
5. Terraform executes: API calls to AWS
6. Terraform saves: State in S3
```

### Step 2.1: Terraform Backend Setup

Why remote state?
- Team collaboration
- State locking (prevents conflicts)
- Backup
- Secure

### Step 2.2: Network Infrastructure

Why VPC design matters?
- Security: Private subnets for apps
- Availability: 3 AZs = 99.99% uptime
- Scalability: /16 CIDR = 65k IPs

### Step 2.3: EKS Cluster

Why EKS over self-managed K8s?
- AWS manages control plane
- Automatic updates
- Integrated with AWS services
- SLA guarantee

How EKS works:
```
Control Plane (AWS managed)
- API Server
- etcd (cluster state)
- Scheduler
- Controller manager

Data Plane (Your managed)
- EC2 worker nodes
- Run your pods
- Auto-scaling groups
```

### Step 2.4: RDS PostgreSQL

Why RDS over PostgreSQL on EC2?
- Automated backups (point-in-time recovery)
- Multi-AZ failover (< 60 seconds)
- Read replicas (scale reads)
- Automated patching
- Monitoring built-in

How Multi-AZ works:
```
Primary Instance (us-east-1a)
  ↓ (synchronous replication)
Standby Instance (us-east-1b)

On failure:
1. AWS detects failure (< 1 min)
2. Promotes standby to primary
3. Updates DNS
4. Total downtime: ~60 seconds
```

---

## Phase 3: Kubernetes Configuration

### Understanding Kubernetes Objects

#### Deployment
**What**: Manages your application pods
**Why**: 
- Declares desired state (e.g., "I want 3 pods")
- Self-healing (restarts crashed pods)
- Rolling updates (zero downtime)

How it works:
```
Deployment
  ↓ (manages)
ReplicaSet
  ↓ (manages)
Pods (3 instances)
```

#### Service
**What**: Network endpoint for pods
**Why**:
- Pods are ephemeral (IPs change)
- Service provides stable IP/DNS
- Load balances across pods

Types:
- ClusterIP: Internal only
- NodePort: Exposes on node
- LoadBalancer: AWS ALB/NLB

#### Ingress
**What**: HTTP(S) routing rules
**Why**:
- One load balancer for many services
- Path-based routing
- SSL termination
- Custom domains

How it works:
```
User → ALB (ingress controller)
  ↓ (routes by path/host)
Service → Pods
```

#### ConfigMap & Secrets
**What**: Configuration data
**Why**:
- Separate config from code
- Different values per environment
- Secrets are encrypted

**ConfigMap**: Non-sensitive (DB host)
**Secret**: Sensitive (DB password)

#### HorizontalPodAutoscaler (HPA)
**What**: Auto-scales pods based on metrics
**Why**:
- Handle traffic spikes
- Save money during low traffic
- Automatic, no manual intervention

How it works:
```
Every 15 seconds:
1. Check CPU/Memory usage
2. If > 80%: Add pods
3. If < 30%: Remove pods
4. Respects min/max limits
```

---

## Phase 4: CI/CD Pipeline

### GitHub Actions Workflow

Why GitHub Actions?
- Native Git integration
- Free for public repos
- Secrets management
- Matrix builds
- Reusable workflows

### CI/CD Flow Explanation

```
1. TRIGGER
   - Push to main/staging/dev branch
   - Pull request opened
   
2. CHECKOUT CODE
   - Clones your repo
   
3. RUN TESTS
   - Unit tests (pytest)
   - Integration tests
   - Coverage report
   
4. CODE QUALITY
   - Linting (flake8, black)
   - Security scan (bandit)
   - Complexity check
   
5. BUILD DOCKER IMAGE
   - Multi-stage build
   - Tag with git SHA
   
6. SCAN IMAGE
   - Vulnerability scan (Trivy)
   - Fail if HIGH/CRITICAL
   
7. PUSH TO ECR
   - Authenticate with AWS
   - Push image
   
8. UPDATE K8S
   - Update image tag in Helm
   - Apply changes
   
9. VERIFY DEPLOYMENT
   - Wait for rollout
   - Check health endpoint
   - Smoke tests
   
10. NOTIFY
    - Slack message
    - GitHub status
```

### How Each Stage Works Internally

#### Testing Stage
```yaml
- name: Run Tests
  run: |
    pytest --cov=. --cov-report=xml
    coverage report --fail-under=80
```

**What happens:**
1. pytest discovers all test files
2. Runs each test in isolation
3. Tracks which lines were executed
4. Generates coverage report
5. Fails if < 80% coverage

**Why important:**
- Catches bugs before production
- Prevents regressions
- Documents expected behavior

#### Security Scanning
```yaml
- name: Security Scan
  run: |
    bandit -r src/
    trivy image $IMAGE
```

**Bandit** scans Python code for:
- SQL injection vulnerabilities
- Hardcoded passwords
- Insecure functions
- Shell injection risks

**Trivy** scans Docker image for:
- Known CVEs in dependencies
- Outdated packages
- Misconfigurations

**Why critical:**
- 85% of breaches use known vulnerabilities
- Automated scanning catches human errors
- Compliance requirements

#### Container Building
```dockerfile
# Stage 1: Builder
FROM python:3.11 as builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*
COPY . .
```

**Why multi-stage:**
- Builder stage: 1.2GB (has build tools)
- Runtime stage: 350MB (only app + deps)
- 70% size reduction
- Faster deploys, less storage cost

#### Deployment Verification
```yaml
- name: Verify Deployment
  run: |
    kubectl rollout status deployment/django-api
    kubectl wait --for=condition=ready pod -l app=django-api
    curl https://api.yourdomain.com/health/
```

**What happens:**
1. Watches deployment progress
2. Waits for pods to be ready
3. Hits health endpoint
4. Fails if any step fails

**Why important:**
- Catches deployment failures immediately
- Prevents bad deploys from going live
- Automated rollback if verification fails

---

## Phase 5: Observability Stack

### The Three Pillars of Observability

#### 1. Logging (What happened?)
**Tools**: CloudWatch Logs + Fluent Bit

How it works:
```
Django app logs
  ↓ (stdout/stderr)
Fluent Bit (sidecar container)
  ↓ (ships logs)
CloudWatch Logs
  ↓ (query with)
CloudWatch Insights
```

**What you can do:**
```sql
-- Find all errors in last hour
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100

-- Track slow requests
fields @timestamp, request_time
| filter request_time > 1000
| stats avg(request_time) by endpoint
```

#### 2. Metrics (How much/many?)
**Tools**: Prometheus + Grafana

How it works:
```
Django app
  ↓ (exports /metrics)
Prometheus (scrapes every 15s)
  ↓ (stores time-series)
Grafana (visualizes)
```

**Metrics tracked:**
- Request rate (req/sec)
- Error rate (%)
- Response time (p50, p95, p99)
- Database queries
- Cache hit rate
- Queue length

**Why important:**
```
Without metrics:
- Is the app slow? ¯\_(ツ)_/¯
- How many users? No idea
- When did it start? Unknown

With metrics:
- Response time jumped to 2s at 3pm
- 500 errors spiked 300%
- Database queries doubled
```

#### 3. Tracing (Where is time spent?)
**Tools**: AWS X-Ray

How it works:
```
Request comes in
  ↓ (generates trace ID)
Django view
  ↓ (segment)
Database query (subsegment)
  ↓ (segment)
Redis call (subsegment)
  ↓ (segment)
External API (subsegment)
  ↓
Response sent

X-Ray visualizes entire flow
```

**Example trace:**
```
Total: 1.2s
├─ Django view: 0.05s
├─ DB query 1: 0.8s ← SLOW!
├─ Redis get: 0.02s
├─ DB query 2: 0.3s
└─ Render response: 0.03s
```

**Why critical:**
- Finds bottlenecks instantly
- Tracks cross-service calls
- Debugging production issues

### Alerting

**Prometheus AlertManager** → Slack/PagerDuty

Alert rules:
```yaml
# High error rate
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
for: 5m
annotations:
  summary: "High error rate detected"

# Pod down
alert: PodDown
expr: up{job="django-api"} == 0
for: 1m
annotations:
  summary: "Django API pod is down"

# High memory
alert: HighMemory
expr: container_memory_usage_bytes > 1.5e9
for: 10m
```

---

## Phase 6: Production Deployment

### Deployment Strategies

#### 1. Rolling Update (Default)
```
Old pods: v1 v1 v1
          ↓
         v1 v1 v2 (start 1 new)
          ↓
         v1 v2 v2 (stop 1 old)
          ↓
         v2 v2 v2 (complete)
```

**Pros**: Simple, built-in
**Cons**: Brief mix of versions

#### 2. Canary Deployment (Recommended)
```
Traffic split:
90% → v1 pods (stable)
10% → v2 pod (canary)

Monitor for 5 minutes:
- Error rate OK?
- Latency OK?
- No alerts?

If good:
50% → v1
50% → v2

Monitor 5 more minutes...

If good:
100% → v2
```

**Pros**: Safe, gradual, easy rollback
**Cons**: More complex

Implementation with Flagger:
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: django-api
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: django-api
  service:
    port: 8000
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
    - name: request-duration
      thresholdRange:
        max: 500
```

**How it works:**
1. Deploy v2
2. Route 10% traffic
3. Measure success rate & latency
4. If metrics good: Increase to 20%
5. Repeat until 100%
6. If metrics bad: Rollback

#### 3. Blue-Green Deployment
```
Blue environment (v1) ← 100% traffic
Green environment (v2) ← 0% traffic

Test green environment
↓
Switch traffic to green
↓
Keep blue running for rollback
```

**Pros**: Instant rollback, full testing
**Cons**: 2x resources

---

## Phase 7: Monitoring & Operations

### Key Dashboards

#### 1. Application Dashboard
Metrics to track:
- Request rate (req/s)
- Error rate (%)
- P50, P95, P99 latency
- Apdex score (user satisfaction)

#### 2. Infrastructure Dashboard
- CPU usage per pod
- Memory usage per pod
- Disk I/O
- Network traffic
- Pod restart count

#### 3. Business Metrics
- Active users
- API calls by endpoint
- Conversion rate
- Revenue (if applicable)

### Incident Response

**Runbook Template:**

```markdown
## High Error Rate Alert

### Symptoms
- Error rate > 5% for 5 minutes
- Users seeing 500 errors

### Investigation
1. Check error logs:
   aws logs tail /aws/eks/django-api --follow
   
2. Check recent deployments:
   kubectl rollout history deployment/django-api
   
3. Check resource usage:
   kubectl top pods

### Common Causes
- Recent deployment (bad code)
- Database connection pool exhausted
- External API down
- Out of memory

### Remediation
- If recent deploy: Rollback
  kubectl rollout undo deployment/django-api
  
- If DB issue: Scale up connections
- If memory: Increase limits or add pods

### Prevention
- Add more tests
- Increase staging environment testing
- Add canary deployment
```

### Cost Optimization

**Monthly Cost Breakdown** (example):

```
EKS Control Plane: $75
EC2 Nodes (3x t3.medium): $90
RDS (db.t3.medium Multi-AZ): $130
ElastiCache (cache.t3.micro): $25
ALB: $20
Data Transfer: $30
S3: $10
CloudWatch: $15
Total: ~$395/month
```

**Optimization strategies:**
1. Use Spot Instances for worker pods (60% savings)
2. Right-size instances (monitoring shows actual usage)
3. Use S3 Intelligent-Tiering
4. Enable RDS auto-pause for dev/staging
5. Compress logs before shipping

---

## Summary: Level 1 → Level 5 Transformation

| Aspect | Level 1 (Your Current) | Level 5 (This Guide) |
|--------|----------------------|---------------------|
| **Deployment** | SSH + git pull | Automated CI/CD, canary |
| **Scaling** | Manual | Auto-scaling HPA |
| **Monitoring** | SSH to check logs | CloudWatch, Prometheus, X-Ray |
| **Reliability** | Single server | Multi-AZ, self-healing |
| **Security** | .env files | Secrets Manager, IAM, scanning |
| **Recovery** | Manual backup | Automated backups, PITR |
| **Cost** | ~$30/month | ~$400/month |
| **Uptime** | 95% | 99.95% |
| **Team Size** | 1-2 | 10+ |

**What you gain:**
- ✅ Sleep at night (auto-healing)
- ✅ Deploy 10x/day (CI/CD)
- ✅ Handle 100x traffic (auto-scaling)
- ✅ Debug issues in minutes (observability)
- ✅ Zero-downtime deploys
- ✅ SOC2 compliance ready
- ✅ Team can collaborate

**What it costs:**
- 💰 More AWS bill (~$400/month for small app)
- 📚 Learning curve (2-4 weeks)
- 🔧 More complexity (managed by tools)

**When to make the jump:**
- Revenue > $10k/month
- Team size > 3
- Users complain about downtime
- Need to deploy multiple times/day
- Compliance requirements
