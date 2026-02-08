# Architecture Deep Dive

## How Everything Works Together

### Request Flow (What Happens When a User Visits Your API)

```
User's Browser
    ↓ HTTPS Request (api.yourdomain.com/api/users/)
    ↓
┌─────────────────────────────────────────────────┐
│ AWS Route 53 (DNS)                              │
│ api.yourdomain.com → ALB IP address             │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ AWS WAF (Web Application Firewall)              │
│ - Blocks SQL injection attempts                 │
│ - Rate limiting                                  │
│ - DDoS protection                                │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ CloudFront CDN (Optional)                       │
│ - Caches static content                         │
│ - SSL/TLS termination                           │
│ - Global edge locations                         │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Application Load Balancer (ALB)                 │
│ - Distributes traffic across pods               │
│ - Health checks                                  │
│ - SSL/TLS termination                           │
│ - Sticky sessions                                │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Kubernetes Ingress Controller                   │
│ - Routes requests based on path                 │
│ - /api/users/ → django-api service              │
│ - /admin/ → django-api service                  │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Kubernetes Service (ClusterIP)                  │
│ - Internal load balancer                        │
│ - Stable IP address                              │
│ - Selects pods by label: app=django-api         │
└─────────────────────────────────────────────────┘
    ↓
    ├─→ Pod 1 (10.0.1.10) ──→ Django + Gunicorn
    ├─→ Pod 2 (10.0.1.11) ──→ Django + Gunicorn
    └─→ Pod 3 (10.0.1.12) ──→ Django + Gunicorn
         ↓
         ├─→ Database Query → RDS PostgreSQL
         ├─→ Cache Check → ElastiCache Redis
         ├─→ File Storage → S3
         └─→ Background Task → Celery Queue
              ↓
    ┌─────────────────────┐
    │ Celery Worker Pods  │
    │ - Process tasks     │
    │ - Send emails       │
    │ - Generate reports  │
    └─────────────────────┘
         ↓
    Response back to user
```

**Timeline:**
1. DNS lookup: 20ms
2. CloudFront (if cached): 10ms → **Total: 30ms** ✓
3. CloudFront (if not cached): Continue...
4. ALB routing: 5ms
5. Ingress routing: 2ms
6. Service routing: 1ms
7. Django processing: 50-200ms
8. Total: **78-228ms** (excellent!)

---

## How Auto-Scaling Works

### Horizontal Pod Autoscaler (HPA)

**The Problem:**
- 9 AM: 10 requests/second → 3 pods enough
- 12 PM: 100 requests/second → 3 pods overloaded!
- Need to automatically add more pods

**How HPA Works:**

```
Every 15 seconds, HPA does this:

1. Check current metrics:
   - Average CPU usage across all pods
   - Average memory usage
   - Custom metrics (request rate, queue length)

2. Calculate desired pods:
   Current CPU: 85%
   Target CPU: 70%
   Current pods: 3
   
   Desired = Current × (Current Metric / Target Metric)
   Desired = 3 × (85% / 70%)
   Desired = 3.64 → 4 pods

3. Tell Kubernetes to scale:
   kubectl scale deployment django-api --replicas=4

4. Kubernetes starts new pod:
   - Schedules on node with capacity
   - Pulls Docker image (if not cached)
   - Starts container
   - Runs health checks
   - Adds to service endpoints
   
5. New pod ready (30-60 seconds):
   Load balancer starts sending traffic
```

**Configuration:**
```yaml
autoscaling:
  minReplicas: 3      # Never go below this
  maxReplicas: 20     # Never go above this
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # Scale up if > 70%
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80  # Scale up if > 80%
```

**Scale-Up Example:**
```
Time    Pods  CPU%  Action
09:00   3     40%   Normal
10:00   3     55%   Normal
11:00   3     75%   Scale up to 4
11:02   4     60%   Normal
12:00   4     80%   Scale up to 6
12:02   6     55%   Normal
13:00   6     30%   Wait 5 min (stabilization)
13:05   6     30%   Scale down to 4
```

---

## How Auto-Healing Works

### Self-Healing Mechanisms

**1. Liveness Probe Failure**

```
Every 10 seconds, Kubernetes checks:
curl http://pod-ip:8000/health/

If fails 3 times in a row:
1. Mark pod as unhealthy
2. Stop sending traffic to it
3. Kill the pod
4. Start a new pod
5. When new pod ready, add to load balancer

Total downtime for that pod: 30 seconds
User impact: ZERO (other pods still serving)
```

**2. Readiness Probe Failure**

```
Every 5 seconds, Kubernetes checks:
curl http://pod-ip:8000/ready/

If fails (e.g., database connection lost):
1. Remove pod from service endpoints
2. Stop sending traffic
3. Keep pod running
4. Keep checking
5. When passes again, add back to endpoints

This handles temporary issues without restarting
```

**3. Out of Memory (OOM)**

```
If pod uses more memory than limit:
1. Kubernetes kills pod immediately
2. Starts new pod
3. CrashLoopBackOff if keeps happening

Logs show:
"OOMKilled" status
"Exit code 137"
```

**4. Node Failure**

```
If entire EC2 node dies:
1. Kubernetes detects (30 seconds)
2. Marks all pods on that node as "Unknown"
3. Starts replacement pods on other nodes
4. When ready, adds to service
5. AWS Auto Scaling Group starts new node
6. When new node ready, can host more pods
```

**Example Timeline:**
```
11:00:00 - Node 2 dies (all 5 pods on it lost)
11:00:30 - Kubernetes detects failure
11:00:31 - Starts 5 new pods on nodes 1 and 3
11:01:30 - New pods ready, serving traffic
11:05:00 - ASG starts new node to replace node 2
11:10:00 - New node ready, joins cluster

User impact: Slight latency increase for 1-2 minutes
No errors (still had pods on nodes 1 and 3)
```

---

## How Zero-Downtime Deployment Works

### Rolling Update Strategy

**The Goal:** Deploy new code without any downtime

**How It Works:**

```
Old version: v1 (3 pods)
New version: v2

Step 1: Start 1 v2 pod
Pods: v1 v1 v1 v2 (4 total)
Traffic: v1 gets 75%, v2 gets 25%
Wait for v2 pod to pass health checks (30s)

Step 2: Stop 1 v1 pod
Pods: v1 v1 v2 (3 total)
Traffic: v1 gets 66%, v2 gets 34%

Step 3: Start another v2 pod
Pods: v1 v1 v2 v2 (4 total)
Traffic: 50/50 split

Step 4: Stop another v1 pod
Pods: v1 v2 v2 (3 total)

Step 5: Start final v2 pod
Pods: v1 v2 v2 v2 (4 total)

Step 6: Stop final v1 pod
Pods: v2 v2 v2 (3 total)
Done! All v2, zero downtime
```

**Configuration:**
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1       # Can have 1 extra pod during update
    maxUnavailable: 0 # Never have less than desired count
```

**Timeline:**
```
13:00:00 - Developer pushes code
13:10:00 - CI/CD builds image
13:12:00 - Kubernetes starts rolling update
13:12:30 - First v2 pod ready
13:13:00 - First v1 pod stopped
13:13:30 - Second v2 pod ready
13:14:00 - Second v1 pod stopped
13:14:30 - Third v2 pod ready
13:15:00 - Final v1 pod stopped
13:15:00 - Deployment complete

Total deployment time: 3 minutes
Downtime: 0 seconds ✓
```

---

## How Monitoring Works

### Metrics Collection Flow

```
Django Application
    ↓ (exports /metrics endpoint)
django_http_requests_total 1234
django_http_request_duration_seconds_bucket{le="0.1"} 950
django_http_request_duration_seconds_bucket{le="0.5"} 1200
django_db_connections_total 15
...

    ↓ (Prometheus scrapes every 30s)
Prometheus Server
- Stores time-series data
- Evaluates alert rules
- Retention: 15 days

    ↓ (Grafana queries)
Grafana Dashboards
- Visualizes metrics
- Creates graphs
- Shows current state

    ↓ (Alert conditions met?)
AlertManager
- Groups similar alerts
- Deduplicates
- Routes to channels

    ↓
Slack / PagerDuty / Email
```

**Example Alert Evaluation:**

```
Every 1 minute, Prometheus evaluates:

Rule: High Error Rate
Query: 
  sum(rate(django_http_responses_total{status=~"5.."}[5m])) 
  / 
  sum(rate(django_http_responses_total[5m])) 
  > 0.05

Result: 0.07 (7%)
Threshold: 0.05 (5%)
Status: FIRING ← Alert triggered!

AlertManager receives alert:
- Checks if already alerted (no)
- Waits for 'for' duration (5 minutes)
- Still above threshold after 5 min?
- Yes → Send to Slack

Slack message:
"🚨 High Error Rate: 7% (threshold: 5%)
Runbook: https://runbooks.company.com/high-error-rate
Dashboard: https://grafana.company.com/d/django-api"
```

### Log Collection Flow

```
Django Application
    ↓ (logs to stdout/stderr)
print("User 123 logged in")
logger.error("Database connection failed")

    ↓ (Container runtime captures)
Docker/containerd
- Captures all stdout/stderr
- Stores in /var/log/pods/

    ↓ (Fluent Bit reads)
Fluent Bit DaemonSet
- Runs on every node
- Tails log files
- Parses JSON
- Adds metadata (pod name, namespace)

    ↓ (ships to CloudWatch)
CloudWatch Logs
- Log group: /aws/eks/production-eks/django-api
- Log stream: django-api-abc123
- Retention: 30 days

    ↓ (query with)
CloudWatch Insights
fields @timestamp, @message, level, user_id
| filter level = "ERROR"
| filter @timestamp > ago(1h)
| stats count() by error_type
```

### Distributed Tracing

**The Problem:**
```
Request took 2 seconds - why?

Without tracing:
¯\_(ツ)_/¯
```

**With AWS X-Ray:**

```
Request: GET /api/orders/123

Trace ID: 1-67890-abc123

Segments:
├─ ALB (5ms)
├─ Ingress (2ms)
├─ Django View (1,850ms) ← Slow!
│  ├─ Authentication (10ms)
│  ├─ Permission Check (5ms)
│  ├─ Database Query 1 (800ms) ← VERY SLOW!
│  │  SELECT * FROM orders WHERE id=123
│  ├─ Database Query 2 (50ms)
│  │  SELECT * FROM order_items WHERE order_id=123
│  ├─ Redis GET (5ms)
│  ├─ External API call (900ms) ← SLOW!
│  │  POST https://payment-api.com/verify
│  └─ Render Template (80ms)
└─ Response (3ms)

Total: 1,860ms

Insights:
1. Database query needs index on orders.id
2. External API is slow - consider caching
3. Can optimize to < 200ms
```

---

## How Secrets Management Works

### AWS Secrets Manager Integration

**The Problem with .env files:**
```
# .env
SECRET_KEY=super-secret-123
DATABASE_PASSWORD=password123

Problems:
❌ Stored in plain text
❌ In Git history (if committed)
❌ In Docker image (if COPY .env)
❌ Can't rotate without rebuilding
❌ No audit log
```

**With AWS Secrets Manager:**

```
1. Secret stored encrypted in AWS:
   django-api/production/database-url
   └─ Encrypted with KMS key
   └─ Value: {"host": "...", "password": "..."}

2. Django pod needs secret:
   a. Pod has IAM role (IRSA)
   b. Role has permission to read secret
   c. Application calls AWS API:
      boto3.client('secretsmanager').get_secret_value(
          SecretId='django-api/production/database-url'
      )
   d. AWS returns decrypted value
   e. Application uses it

3. Rotation (automatic):
   a. AWS Lambda triggers every 30 days
   b. Creates new password in RDS
   c. Updates secret value
   d. Pods pick up new value on restart
   e. Old password still works (grace period)
   f. Old password disabled after 24 hours
```

**Access Control:**
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",
    "secretsmanager:DescribeSecret"
  ],
  "Resource": [
    "arn:aws:secretsmanager:*:*:secret:django-api/production/*"
  ],
  "Condition": {
    "StringEquals": {
      "aws:RequestedRegion": "us-east-1"
    }
  }
}
```

**Audit Trail:**
```
CloudTrail logs show:
2024-02-08 10:00:00 - User: django-api-pod-role
Action: GetSecretValue
Resource: django-api/production/database-url
Result: Success
Source IP: 10.0.1.45 (pod IP)
```

---

## How Database High Availability Works

### RDS Multi-AZ Architecture

```
Primary Database (us-east-1a)
- Receives all writes
- Serves reads
- Synchronous replication →

Standby Database (us-east-1b)
- Receives replicated data
- Does NOT serve traffic (standby only)
- Automatic failover ready

How Failover Works:

1. Primary fails (11:00:00)
   - Hardware failure
   - Network issue
   - Maintenance

2. RDS detects failure (11:00:30)
   - Health checks fail
   - No response to queries

3. RDS promotes standby (11:00:45)
   - Standby becomes primary
   - Updates DNS record
   - Sends notifications

4. Applications reconnect (11:01:00)
   - DNS TTL expires
   - Apps resolve new IP
   - Connection pools refresh

5. Failover complete (11:01:30)
   - New primary serving traffic
   - RDS starts new standby in original AZ

Total downtime: ~60 seconds
Data loss: ZERO (synchronous replication)
```

### Read Replicas (Optional)

```
For read-heavy workloads:

Primary (writes)
    ↓ (async replication)
├─ Read Replica 1 (reads)
├─ Read Replica 2 (reads)
└─ Read Replica 3 (reads)

Django configuration:
DATABASES = {
    'default': {  # Writes
        'HOST': 'primary.rds.amazonaws.com',
    },
    'replica': {  # Reads
        'HOST': 'replica.rds.amazonaws.com',
    }
}

# Use in code:
User.objects.using('replica').get(id=123)  # Read from replica
user.save(using='default')  # Write to primary
```

---

## Cost Breakdown and Optimization

### Monthly AWS Costs (~$400)

```
Service               Cost/Month    Optimization
────────────────────────────────────────────────────
EKS Control Plane     $75          Fixed cost
                                   (Free tier doesn't apply to EKS)

EC2 Nodes             $90          Use Spot instances: -60% = $36
├─ 3x t3.medium       $30 each     Reserved instances: -40% = $54
└─ 2x Spot            $12          Auto-scaling: Scale to 0 at night

RDS PostgreSQL        $130         Reserved instance: -40% = $78
├─ db.t3.medium       $65          Scale down dev/staging
└─ Multi-AZ replica   $65          Use Aurora Serverless for dev

ElastiCache Redis     $25          Use Graviton2 instances: -20% = $20
                                   Scale down at night

Load Balancer         $20          Share ALB across services
                                   Use single ALB with host routing

Data Transfer         $30          Use CloudFront CDN caching
                                   Reduce inter-AZ transfer

S3 Storage            $10          Intelligent-Tiering
                                   Lifecycle policies

CloudWatch            $15          Reduce log retention (30→7 days)
                                   Aggregate metrics

────────────────────────────────────────────────────
TOTAL                 $395         Optimized: $230/month (-42%)
```

### Cost Optimization Strategies

**1. Use Spot Instances for Workers**
```hcl
# terraform/main.tf
eks_managed_node_groups = {
  spot = {
    instance_types = ["t3.medium", "t3a.medium"]
    capacity_type  = "SPOT"
    min_size       = 0
    max_size       = 10
  }
}
```
Savings: $54/month (60% off)

**2. Auto-Scale Down at Night**
```yaml
# k8s/cronjob-scale-down.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-down-night
spec:
  schedule: "0 22 * * *"  # 10 PM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scale
            image: bitnami/kubectl
            command:
            - kubectl
            - scale
            - deployment/django-api
            - --replicas=1

---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-up-morning
spec:
  schedule: "0 8 * * *"  # 8 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scale
            image: bitnami/kubectl
            command:
            - kubectl
            - scale
            - deployment/django-api
            - --replicas=3
```
Savings: $40/month (14 hours/day at minimum)

**3. Use Reserved Instances**
```
Purchase 1-year reserved instances:
- 3x t3.medium EC2: -40% = save $36/month
- 1x db.t3.medium RDS: -40% = save $52/month
Total savings: $88/month
```

**4. S3 Intelligent-Tiering**
```hcl
lifecycle_rule = [{
  id      = "intelligent-tiering"
  enabled = true
  transition = [{
    days          = 30
    storage_class = "INTELLIGENT_TIERING"
  }]
}]
```
Savings: $3-5/month (automatically moves to cheaper tier)

---

## Comparison: Your Setup vs This Setup

| Aspect | EC2 + Git Pull | This Architecture |
|--------|----------------|-------------------|
| **Infrastructure** | 1 EC2 t3.medium | 3-node EKS cluster + RDS + Redis |
| **Cost** | $30/month | $400/month |
| **Scalability** | Manual, 1 instance | Auto-scales 3-20 pods |
| **Availability** | ~95% (single point of failure) | 99.95% (multi-AZ) |
| **Deployment** | SSH, git pull, restart (5 min, downtime) | git push, automated (10 min, zero downtime) |
| **Rollback** | git revert, restart | kubectl rollout undo (instant) |
| **Monitoring** | SSH, tail logs | Prometheus, Grafana, CloudWatch |
| **Logging** | Local files, SSH to view | Centralized CloudWatch Insights |
| **Alerting** | Manual checking | Automated Slack/PagerDuty alerts |
| **Security** | .env files, manual patches | Secrets Manager, auto-patching |
| **Database** | PostgreSQL on same EC2 | RDS Multi-AZ, automated backups |
| **Caching** | None or local Redis | ElastiCache Redis cluster |
| **File Storage** | Local disk | S3 + CloudFront CDN |
| **Recovery** | Manual backup, pray | Automated backups, point-in-time recovery |
| **Testing** | Production is QA | Full CI/CD with automated tests |
| **Team Size** | 1-2 developers | 10+ developers |
| **Deploys/Day** | 1-2 (risky) | 10+ (safe) |

---

## When to Use This Architecture

### ✅ Use this setup if:
- Revenue > $10,000/month
- Team size > 3 people
- Users complain about downtime
- Need to deploy multiple times per day
- Compliance requirements (SOC2, HIPAA)
- Want to sleep at night

### ❌ Overkill if:
- Personal project / MVP
- < 1,000 users
- < $1,000/month revenue
- Solo developer
- Can tolerate downtime

### 🤔 Middle ground options:
- ECS Fargate (simpler than EKS, 70% of benefits)
- Railway / Render (PaaS, minimal management)
- DigitalOcean App Platform (simple, cheaper)

---

This is the same architecture used by companies with millions of users. You're now operating at the same level as professional engineering teams! 🎉
