"urls "
from django.urls import path
from .views import health, fares, get_fares_uber, get_fares_rapido, get_fares_ola

urlpatterns = [
    path("health/", health),
    path("fares/", fares),
    path("uber/", get_fares_uber),
    path("rapido/", get_fares_rapido),
    path("ola/", get_fares_ola)
]
