# src/config/settings/production.py
"""
Production Django settings with full observability, security, and performance optimization.
"""

import json
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# AWS Configuration
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

# Fetch secrets from AWS Secrets Manager
def get_secret(secret_name):
    """Fetch secret from AWS Secrets Manager"""
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=AWS_REGION
    )
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        raise Exception(f"Error fetching secret {secret_name}: {e}")

# Database configuration from Secrets Manager
db_secrets = get_secret('django-api/production/database-url')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_secrets['database'],
        'USER': db_secrets['username'],
        'PASSWORD': db_secrets['password'],
        'HOST': db_secrets['host'],
        'PORT': db_secrets['port'],
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30 second query timeout
        },
    }
}

# Cache configuration - Redis
REDIS_ENDPOINT = os.getenv('REDIS_ENDPOINT')
REDIS_AUTH_TOKEN = os.getenv('REDIS_AUTH_TOKEN')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'rediss://{REDIS_ENDPOINT}:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': REDIS_AUTH_TOKEN,
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    }
}

# Session configuration - use Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# CSRF
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'https://api.yourdomain.com',
    'https://*.yourdomain.com',
]

# Static files - S3
AWS_STORAGE_BUCKET_NAME_STATIC = os.getenv('AWS_STORAGE_BUCKET_NAME_STATIC')
AWS_STORAGE_BUCKET_NAME_MEDIA = os.getenv('AWS_STORAGE_BUCKET_NAME_MEDIA')
AWS_S3_REGION_NAME = AWS_REGION
AWS_S3_CUSTOM_DOMAIN_STATIC = f'{AWS_STORAGE_BUCKET_NAME_STATIC}.s3.amazonaws.com'
AWS_S3_CUSTOM_DOMAIN_MEDIA = f'{AWS_STORAGE_BUCKET_NAME_MEDIA}.s3.amazonaws.com'

# Static files configuration
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN_STATIC}/'

# Media files configuration
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN_MEDIA}/'

# S3 settings
AWS_DEFAULT_ACL = None  # Use bucket policy
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',  # 1 day cache
}
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = False

# Security Headers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'corsheaders',
    'django_filters',
    'storages',
    
    # Monitoring & Observability
    'django_prometheus',  # Prometheus metrics
    'aws_xray_sdk.ext.django',  # AWS X-Ray tracing
    
    # Your apps
    'apps.core',
    'apps.api',
]

MIDDLEWARE = [
    # Prometheus metrics - must be first
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    
    # AWS X-Ray tracing
    'aws_xray_sdk.ext.django.middleware.XRayMiddleware',
    
    # Security
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    
    # Standard Django
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom middleware
    'apps.core.middleware.RequestLoggingMiddleware',
    'apps.core.middleware.PerformanceMiddleware',
    
    # Prometheus - must be last
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# AWS X-Ray Configuration
XRAY_RECORDER = {
    'AUTO_INSTRUMENT': True,
    'AWS_SDK_ENABLED': True,
    'SAMPLING': True,
    'SAMPLING_RULES': {
        'version': 2,
        'rules': [
            {
                'description': 'Sample all requests',
                'service_name': 'django-api',
                'http_method': '*',
                'url_path': '*',
                'fixed_target': 1,
                'rate': 0.1
            }
        ],
        'default': {
            'fixed_target': 1,
            'rate': 0.1
        }
    }
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'cloudwatch': {
            'class': 'watchtower.CloudWatchLogHandler',
            'log_group': '/aws/eks/production-eks/django-api',
            'stream_name': 'django-{strftime:%Y-%m-%d}',
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'cloudwatch'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'cloudwatch'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'cloudwatch'],
            'level': 'WARNING',  # Log slow queries
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'cloudwatch'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'cloudwatch'],
        'level': 'INFO',
    },
}

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]
CORS_ALLOW_CREDENTIALS = True

# Celery Configuration
CELERY_BROKER_URL = f'rediss://:{REDIS_AUTH_TOKEN}@{REDIS_ENDPOINT}:6379/1'
CELERY_RESULT_BACKEND = f'rediss://:{REDIS_AUTH_TOKEN}@{REDIS_ENDPOINT}:6379/2'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Prevent memory leaks
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('AWS_SES_USERNAME')
EMAIL_HOST_PASSWORD = os.getenv('AWS_SES_PASSWORD')
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'

# Sentry Error Tracking (Optional but recommended)
if os.getenv('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% profiling
        environment='production',
        send_default_pii=False,
    )

# Performance Monitoring
# Database query logging for slow queries
if DEBUG:
    LOGGING['loggers']['django.db.backends']['level'] = 'DEBUG'

# Admin site configuration
ADMIN_URL = os.getenv('ADMIN_URL', 'admin/')  # Obscure admin URL

# Rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Django Prometheus metrics
PROMETHEUS_EXPORT_MIGRATIONS = False
PROMETHEUS_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
