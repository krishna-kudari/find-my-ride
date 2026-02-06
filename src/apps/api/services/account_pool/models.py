"""Service Account Model for DB"""

from django.db import models


class ServiceAccount(models.Model):
    "Service Account Class"

    phone_num: models.CharField = models.CharField(max_length=20)
    client: models.CharField = models.CharField(max_length=20)
    credentials: models.TextField = models.TextField()
    status: models.CharField = models.CharField(max_length=20)
    usage: models.IntegerField = models.IntegerField(default=0)

    def __string__(self):
        return f"${self.phone_num}-${self.client}"
