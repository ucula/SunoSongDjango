from django.db import models
from django.conf import settings


class Library(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library")

    def __str__(self) -> str:
        return f"{self.user} library"