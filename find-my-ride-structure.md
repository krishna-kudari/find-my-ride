# Find-My-Ride Microservice - Project Structure

## Overview
Production-ready Django microservice with scalability, observability, and enterprise features built in.

---

## Project Root Structure

```
find-my-ride/
├── .github/
│   └── workflows/
│       ├── ci-cd.yml                    # GitHub Actions for CI/CD
│       ├── security-scan.yml
│       └── load-test.yml
├── .env.example                         # Environment variables template
├── .gitignore
├── .dockerignore
├── .pre-commit-config.yaml              # Pre-commit hooks (black, mypy, etc.)
├── pyproject.toml                       # Poetry configuration with all deps
├── poetry.lock                          # Locked dependencies
├── Dockerfile                           # Production Docker image
├── docker-compose.yml                   # Local development stack
├── docker-compose.prod.yml              # Production stack
├── manage.py                            # Django management
├── README.md
├── DEPLOYMENT.md                        # AWS EC2 deployment guide
├── ARCHITECTURE.md                      # System architecture docs
├── requirements/
│   ├── base.txt                         # Base dependencies
│   ├── dev.txt                          # Development extras
│   ├── prod.txt                         # Production extras
│   └── test.txt                         # Testing dependencies
│
├── src/
│   ├── __init__.py
│   ├── manage.py
│   ├── wsgi.py                          # WSGI entry point
│   ├── asgi.py                          # ASGI entry point (for async)
│   │
│   ├── config/                          # Django settings
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # Common settings
│   │   │   ├── development.py
│   │   │   ├── production.py
│   │   │   ├── testing.py
│   │   │   └── aws.py                   # AWS-specific config
│   │   ├── urls.py                      # Root URL config
│   │   ├── middleware.py                # Custom middleware
│   │   └── constants.py                 # App-wide constants
│   │
│   ├── apps/
│   │   │
│   │   ├── core/                        # Shared/reusable app
│   │   │   ├── migrations/
│   │   │   ├── __init__.py
│   │   │   ├── models.py                # Base models
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests/
│   │   │       ├── test_models.py
│   │   │       └── test_views.py
│   │   │
│   │   ├── rides/                       # Rides management
│   │   │   ├── migrations/
│   │   │   ├── __init__.py
│   │   │   ├── models.py                # Ride, Location, RideStatus
│   │   │   ├── views.py                 # ViewSets and APIViews
│   │   │   ├── serializers.py           # DRF serializers with types
│   │   │   ├── filters.py               # Filtering logic
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── services.py              # Business logic
│   │   │   ├── tasks.py                 # Celery tasks
│   │   │   └── tests/
│   │   │       ├── test_models.py
│   │   │       ├── test_views.py
│   │   │       ├── test_services.py
│   │   │       └── test_integration.py
│   │   │
│   │   ├── matching/                    # Ride matching algorithm
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   ├── services.py              # Matching logic
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests/
│   │   │       ├── test_matching.py
│   │   │       └── test_algorithm.py
│   │   │
│   │   ├── payments/                    # Payment processing
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   ├── services.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── adapters/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── stripe.py            # Stripe adapter
│   │   │   │   ├── razorpay.py          # Razorpay adapter
│   │   │   │   └── paypal.py            # PayPal adapter
│   │   │   └── tests/
│   │   │       └── test_payments.py
│   │   │
│   │   ├── notifications/               # Email, SMS, Push
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   ├── services.py
│   │   │   ├── urls.py
│   │   │   ├── tasks.py                 # Celery tasks for async
│   │   │   ├── adapters/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── email.py             # SMTP / SendGrid
│   │   │   │   ├── sms.py               # Twilio / AWS SNS
│   │   │   │   └── push.py              # Firebase Cloud Messaging
│   │   │   └── tests/
│   │   │
│   │   ├── users/                       # User management
│   │   │   ├── migrations/
│   │   │   ├── __init__.py
│   │   │   ├── models.py                # Custom User model
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests/
│   │   │
│   │   ├── auth/                        # Authentication & Authorization
│   │   │   ├── __init__.py
│   │   │   ├── models.py                # Token, OAuth models
│   │   │   ├── views.py                 # Login, Register, Refresh
│   │   │   ├── serializers.py
│   │   │   ├── authentication.py        # Custom auth classes
│   │   │   ├── permissions.py           # Custom permissions
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   ├── services.py
│   │   │   └── tests/
│   │   │       ├── test_auth.py
│   │   │       └── test_permissions.py
│   │   │
│   │   └── health/                      # Health checks
│   │       ├── __init__.py
│   │       ├── views.py
│   │       ├── checks.py                # Custom health checks
│   │       └── urls.py
│   │
│   ├── adapters/                        # Third-party integrations
│   │   ├── __init__.py
│   │   ├── base.py                      # Base adapter interface
│   │   ├── google_maps/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── distance.py
│   │   │   └── geocoding.py
│   │   ├── aws/
│   │   │   ├── __init__.py
│   │   │   ├── s3.py
│   │   │   ├── sqs.py
│   │   │   └── cloudwatch.py
│   │   └── monitoring/
│   │       ├── __init__.py
│   │       ├── datadog.py
│   │       ├── sentry.py
│   │       └── prometheus.py
│   │
│   ├── clients/                         # Service clients (SDK/REST)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── shared_auth_client.py        # Client for shared auth service
│   │
│   ├── common/                          # Shared utilities
│   │   ├── __init__.py
│   │   ├── exceptions.py                # Custom exceptions
│   │   ├── utils.py                     # Utility functions
│   │   ├── decorators.py                # Custom decorators
│   │   ├── pagination.py                # DRF pagination
│   │   ├── throttling.py                # Rate limiting
│   │   ├── serializers.py               # Base serializers
│   │   ├── mixins.py                    # DRF mixins
│   │   ├── validators.py                # Custom validators
│   │   └── enums.py                     # Enumerations
│   │
│   ├── logging/                         # Logging configuration
│   │   ├── __init__.py
│   │   ├── formatters.py
│   │   └── middleware.py                # Request/response logging
│   │
│   ├── metrics/                         # Metrics & Observability
│   │   ├── __init__.py
│   │   ├── prometheus.py
│   │   ├── events.py                    # Event tracking
│   │   └── analytics.py                 # Custom analytics
│   │
│   └── static/
│       └── .gitkeep
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Pytest fixtures
│   ├── factories.py                     # Test data factories
│   ├── fixtures.py
│   ├── mocks.py
│   ├── integration/
│   │   ├── test_rides_flow.py
│   │   ├── test_payment_flow.py
│   │   └── test_matching_flow.py
│   └── performance/
│       └── test_load.py
│
├── scripts/
│   ├── __init__.py
│   ├── deploy.sh                        # Deployment script
│   ├── migrate.sh                       # Database migration
│   ├── seed_data.py                     # Seed initial data
│   ├── generate_fixtures.py
│   └── performance_test.py
│
├── infrastructure/
│   ├── terraform/                       # Infrastructure as Code
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── ec2.tf                       # EC2 instance config
│   │   ├── rds.tf                       # Database
│   │   ├── elasticache.tf               # Redis cache
│   │   ├── alb.tf                       # Load balancer
│   │   ├── security_groups.tf
│   │   ├── iam.tf
│   │   └── environments/
│   │       ├── dev.tfvars
│   │       ├── staging.tfvars
│   │       └── prod.tfvars
│   ├── nginx/
│   │   ├── nginx.conf
│   │   ├── default.conf
│   │   └── ssl.conf
│   ├── supervisord/
│   │   ├── supervisord.conf
│   │   ├── gunicorn.conf
│   │   ├── celery-worker.conf
│   │   └── celery-beat.conf
│   └── systemd/
│       ├── find-my-ride.service
│       ├── find-my-ride-celery.service
│       └── find-my-ride-beat.service
│
├── docs/
│   ├── API.md                           # API documentation
│   ├── CONTRIBUTING.md
│   ├── SETUP.md                         # Local setup guide
│   ├── DEPLOYMENT.md                    # Production deployment
│   ├── ARCHITECTURE.md                  # System design
│   ├── TESTING.md                       # Testing strategy
│   ├── MONITORING.md                    # Monitoring setup
│   └── diagrams/
│       ├── system_architecture.md
│       └── database_schema.md
│
└── tools/
    ├── load_test.py                     # Locust load testing
    └── monitoring_dashboard.py
```

---

## Key Files Detailed

### 1. `pyproject.toml` - Poetry Configuration

```toml
[tool.poetry]
name = "find-my-ride"
version = "1.0.0"
description = "Ride-sharing microservice"
authors = ["Your Name <email@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"

# Django & DRF
django = "^4.2"
djangorestframework = "^3.14"
django-cors-headers = "^4.0"
django-filter = "^23.1"

# Database & ORM
psycopg2-binary = "^2.9"  # PostgreSQL
sqlalchemy = "^2.0"

# Authentication
djangorestframework-simplejwt = "^5.2"
python-decouple = "^3.8"
cryptography = "^40.0"

# Async & Background Jobs
celery = "^5.3"
redis = "^4.5"

# Validation & Types
pydantic = "^2.0"
marshmallow = "^3.19"

# HTTP & Networking
httpx = "^0.24"
requests = "^2.31"

# AWS
boto3 = "^1.26"
django-storages = "^1.13"

# Monitoring & Observability
prometheus-client = "^0.17"
sentry-sdk = "^1.25"
python-json-logger = "^2.0"
opentelemetry-api = "^1.17"
opentelemetry-sdk = "^1.17"
opentelemetry-exporter-jaeger = "^1.17"

# Utilities
python-dateutil = "^2.8"
pytz = "^2023.3"
Pillow = "^9.5"
setuptools = "^67.0"

[tool.poetry.group.dev.dependencies]
# Testing
pytest = "^7.3"
pytest-django = "^4.5"
pytest-cov = "^4.1"
pytest-asyncio = "^0.21"
factory-boy = "^3.2"
faker = "^18.0"
responses = "^0.23"

# Code Quality
black = "^23.0"
isort = "^5.12"
flake8 = "^6.0"
mypy = "^1.0"
django-stubs = "^4.2"
djangorestframework-stubs = "^3.14"
pylint = "^2.17"
pylint-django = "^2.5"

# Development Tools
django-debug-toolbar = "^4.0"
django-extensions = "^3.2"
ipython = "^8.12"
ptpython = "^3.0"

# Documentation
sphinx = "^6.0"
sphinx-rtd-theme = "^1.2"

[tool.poetry.group.prod.dependencies]
gunicorn = "^20.1"
whitenoise = "^6.4"
psycopg2-binary = "^2.9"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
ignore_missing_imports = false

[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.testing"
testpaths = ["tests", "src"]
python_files = "test_*.py"
addopts = "--cov=src --cov-report=html --strict-markers"

[tool.coverage.run]
source = ["src"]
omit = ["*/migrations/*", "*/tests/*"]
```

### 2. `Dockerfile` - Production Image

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./

RUN pip install poetry && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/requirements.txt .

RUN pip install -r requirements.txt && \
    pip install gunicorn

COPY src/ .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health/ || exit 1

EXPOSE ${PORT}

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "config.wsgi:application"]
```

### 3. `docker-compose.yml` - Local Development

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: find_my_ride
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             python manage.py runserver 0.0.0.0:8000"
    environment:
      DEBUG: "True"
      DATABASE_URL: postgresql://postgres:postgres@db:5432/find_my_ride
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: dev-secret-key-change-in-production
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery:
    build: .
    command: celery -A config worker -l info
    environment:
      DEBUG: "False"
      DATABASE_URL: postgresql://postgres:postgres@db:5432/find_my_ride
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: dev-secret-key-change-in-production
    depends_on:
      - db
      - redis
    volumes:
      - .:/app

  celery-beat:
    build: .
    command: celery -A config beat -l info
    environment:
      DEBUG: "False"
      DATABASE_URL: postgresql://postgres:postgres@db:5432/find_my_ride
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: dev-secret-key-change-in-production
    depends_on:
      - db
      - redis
    volumes:
      - .:/app

volumes:
  postgres_data:
```

---

## Database Architecture

### Models Structure

```python
# Minimal example structure

# Core/Base Models
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# Rides App
class Ride(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    driver = models.ForeignKey(User, on_delete=models.CASCADE)
    passenger = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    origin = models.PointField()  # GeoDjango
    destination = models.PointField()
    status = models.CharField(max_length=20, choices=RideStatus.choices)
    scheduled_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    fare = models.DecimalField(max_digits=10, decimal_places=2)

# Payments
class Payment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=255, unique=True)
```

---

## Authentication Strategy

### Shared Auth Service Integration

```python
# src/clients/shared_auth_client.py

from typing import Optional, TypedDict
import httpx

class TokenResponse(TypedDict):
    access_token: str
    refresh_token: str
    expires_in: int

class SharedAuthClient:
    """Client for centralized auth service"""
    
    def __init__(self, base_url: str, service_key: str):
        self.base_url = base_url
        self.service_key = service_key
        self.client = httpx.AsyncClient()
    
    async def validate_token(self, token: str) -> Optional[dict]:
        """Validate JWT from shared auth service"""
        response = await self.client.post(
            f"{self.base_url}/validate",
            json={"token": token},
            headers={"X-Service-Key": self.service_key}
        )
        return response.json() if response.status_code == 200 else None
    
    async def refresh_token(self, refresh_token: str) -> Optional[TokenResponse]:
        """Refresh token"""
        response = await self.client.post(
            f"{self.base_url}/refresh",
            json={"refresh_token": refresh_token}
        )
        return response.json() if response.status_code == 200 else None
```

---

## Rate Limiting Strategy

```python
# src/common/throttling.py

from rest_framework.throttling import SimpleRateThrottle
from typing import Optional

class RideCreationThrottle(SimpleRateThrottle):
    scope = "ride_creation"
    THROTTLE_RATES = {
        "ride_creation": "10/hour",
        "ride_search": "30/minute",
        "payment": "5/minute",
    }

class BurstThrottle(SimpleRateThrottle):
    scope = "burst"
    THROTTLE_RATES = {"burst": "100/hour"}
```

---

## Monitoring & Observability Setup

### Health Checks

```python
# src/apps/health/checks.py

from django.core.checks import run_checks, Tags
from django.db import connections
from django.core.cache import cache
import redis

class HealthCheckService:
    @staticmethod
    def check_database() -> dict:
        """Check database connectivity"""
        try:
            connections["default"].ensure_connection()
            return {"status": "healthy", "service": "database"}
        except Exception as e:
            return {"status": "unhealthy", "service": "database", "error": str(e)}
    
    @staticmethod
    def check_redis() -> dict:
        """Check Redis connectivity"""
        try:
            r = redis.Redis.from_url("redis://localhost:6379")
            r.ping()
            return {"status": "healthy", "service": "redis"}
        except Exception as e:
            return {"status": "unhealthy", "service": "redis", "error": str(e)}
```

### Prometheus Metrics

```python
# src/metrics/prometheus.py

from prometheus_client import Counter, Histogram, Gauge
import time

request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_latency = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

ride_matches = Counter(
    'ride_matches_total',
    'Total ride matches',
    ['status']
)

active_rides = Gauge(
    'active_rides',
    'Number of active rides'
)
```

---

## Load Testing with Locust

```python
# tools/load_test.py

from locust import HttpUser, task, between
from locust import TaskSet

class RideUser(TaskSet):
    @task(3)
    def list_rides(self):
        self.client.get("/api/rides/")
    
    @task(1)
    def create_ride(self):
        self.client.post(
            "/api/rides/",
            json={
                "origin": "10.0,20.0",
                "destination": "11.0,21.0",
                "scheduled_at": "2024-02-03T10:00:00Z"
            }
        )
    
    @task(2)
    def match_rides(self):
        self.client.get("/api/matching/search/")

class ApiLoadTest(HttpUser):
    tasks = [RideUser]
    wait_time = between(1, 5)
```

---

## Deployment on AWS EC2

### Key Components

1. **EC2 Instance**: t3.medium (auto-scaling group)
2. **RDS**: PostgreSQL 15 (Multi-AZ in production)
3. **ElastiCache**: Redis for sessions/cache
4. **ALB**: Application Load Balancer with SSL
5. **CloudWatch**: Monitoring and logging
6. **S3**: Static files and media storage
7. **Route53**: DNS management
8. **IAM Roles**: Service-specific permissions

### Environment Variables (.env)

```bash
# Django
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=api.krishna-kudari.link

# Database
DATABASE_URL=postgresql://user:password@rds-endpoint:5432/find_my_ride

# Redis
REDIS_URL=redis://elasticache-endpoint:6379/0

# AWS
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=find-my-ride-assets
AWS_REGION=us-east-1

# Authentication
JWT_SECRET=your-jwt-secret
SHARED_AUTH_SERVICE_URL=https://auth.krishna-kudari.link
SHARED_AUTH_SERVICE_KEY=service-key

# Third-party APIs
GOOGLE_MAPS_API_KEY=your-key
STRIPE_SECRET_KEY=your-key
SENTRY_DSN=https://your-dsn

# Observability
PROMETHEUS_ENABLED=True
DATADOG_API_KEY=your-key
```

---

## Testing Strategy

### Test Hierarchy

1. **Unit Tests**: Models, serializers, utilities (~70%)
2. **Integration Tests**: Service interactions, API flows (~20%)
3. **E2E Tests**: Full ride lifecycle (~10%)

### Example Test

```python
# tests/integration/test_rides_flow.py

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from factory import DjangoModelFactory

class RideFactory(DjangoModelFactory):
    class Meta:
        model = 'rides.Ride'

@pytest.mark.django_db
class TestRideFlow:
    def test_complete_ride_lifecycle(self, api_client: APIClient):
        # Create ride
        response = api_client.post('/api/rides/', {
            'origin': '10.0,20.0',
            'destination': '11.0,21.0'
        })
        assert response.status_code == 201
        ride_id = response.json()['id']
        
        # Accept ride
        response = api_client.patch(f'/api/rides/{ride_id}/', {
            'status': 'accepted'
        })
        assert response.status_code == 200
        
        # Complete ride
        response = api_client.patch(f'/api/rides/{ride_id}/', {
            'status': 'completed'
        })
        assert response.status_code == 200
```

---

## CI/CD Pipeline (.github/workflows/ci-cd.yml)

```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      
      - name: Run tests
        run: poetry run pytest
      
      - name: Type check
        run: poetry run mypy src
      
      - name: Lint
        run: poetry run flake8 src
```

---

## Best Practices Summary

✅ **Type Safety**: All functions typed, mypy strict mode enabled  
✅ **Testing**: >80% code coverage, integration & unit tests  
✅ **Scalability**: Horizontally scalable with load balancing  
✅ **Security**: JWT auth, rate limiting, CORS, HTTPS  
✅ **Monitoring**: Prometheus, Sentry, CloudWatch integration  
✅ **Async**: Celery for long-running tasks  
✅ **Caching**: Redis for sessions and performance  
✅ **Documentation**: Comprehensive API docs, deployment guides  
✅ **CI/CD**: GitHub Actions for automated testing/deployment  
✅ **Infrastructure**: Terraform for IaC on AWS  

---

## Quick Start Commands

```bash
# Setup
poetry install
poetry run python src/manage.py migrate
poetry run python src/manage.py createsuperuser

# Development
docker-compose up
poetry run python src/manage.py runserver

# Testing
poetry run pytest --cov=src
poetry run mypy src

# Deployment
./scripts/deploy.sh production

# Load testing
poetry run locust -f tools/load_test.py --host=http://localhost:8000
```

---

## Shared Auth Service Recommendation

For managing auth across multiple projects, consider:

1. **Dedicated Auth Microservice** (Recommended)
   - Centralized user management
   - JWT token management
   - OAuth2/OIDC support
   - Audit logging

2. **API Gateway Pattern**
   - Kong, AWS API Gateway, or Nginx-based auth

3. **Service Mesh**
   - Istio for distributed authentication/authorization

---

## Next Steps

1. Initialize project: `poetry new find-my-ride`
2. Set up pre-commit hooks for code quality
3. Configure AWS resources using Terraform
4. Set up monitoring dashboards (CloudWatch/Datadog)
5. Implement shared auth client integration
6. Load test before production deployment
