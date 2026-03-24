from django.conf import settings
from django.db import models


class Voice(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"


class GenForm(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gen_forms")
    title = models.CharField(max_length=255)
    mood_tone = models.CharField(max_length=255)
    genre = models.CharField(max_length=255)
    voice = models.CharField(max_length=10, choices=Voice.choices)
    description = models.TextField()

    def __str__(self) -> str:
        return self.title