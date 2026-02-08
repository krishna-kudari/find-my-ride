# src/apps/core/views/health.py
"""
Health check endpoints for Kubernetes liveness and readiness probes.
"""

import logging
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Liveness probe - checks if the application is alive.
    Returns 200 if the application can respond to requests.
    
    Used by Kubernetes to know when to restart the pod.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'django-api',
    }, status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Readiness probe - checks if the application is ready to serve traffic.
    Verifies critical dependencies (database, cache).
    
    Used by Kubernetes to know when to route traffic to the pod.
    Returns 200 if ready, 503 if not ready.
    """
    checks = {
        'database': False,
        'cache': False,
    }
    
    errors = []
    
    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks['database'] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        errors.append(f"database: {str(e)}")
    
    # Check cache connectivity
    try:
        cache.set('health_check', 'ok', timeout=10)
        value = cache.get('health_check')
        if value == 'ok':
            checks['cache'] = True
        else:
            errors.append("cache: unexpected value")
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        errors.append(f"cache: {str(e)}")
    
    # Overall status
    all_healthy = all(checks.values())
    
    response_data = {
        'status': 'ready' if all_healthy else 'not_ready',
        'checks': checks,
    }
    
    if errors:
        response_data['errors'] = errors
    
    status_code = 200 if all_healthy else 503
    
    return JsonResponse(response_data, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def metrics(request):
    """
    Application metrics endpoint for monitoring.
    This is exposed via django-prometheus at /metrics.
    """
    # The actual metrics are served by django-prometheus
    # This is just a placeholder to document the endpoint
    from django_prometheus.exports import ExportToDjangoView
    return ExportToDjangoView(request)


@api_view(['GET'])
@permission_classes([AllowAny])
def status(request):
    """
    Detailed status endpoint for monitoring dashboards.
    Returns application version, build info, and system status.
    """
    import os
    import platform
    import sys
    from django import get_version
    
    return JsonResponse({
        'service': 'django-api',
        'status': 'operational',
        'version': os.getenv('APP_VERSION', 'unknown'),
        'build': {
            'commit': os.getenv('GIT_COMMIT', 'unknown'),
            'branch': os.getenv('GIT_BRANCH', 'unknown'),
            'build_time': os.getenv('BUILD_TIME', 'unknown'),
        },
        'environment': {
            'python_version': sys.version,
            'django_version': get_version(),
            'platform': platform.platform(),
        },
    })
