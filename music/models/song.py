from django.db import models
from django.db.models import Q

from .gen_form import GenForm
from .library import Library


class Status(models.TextChoices):
    GENERATING = "generating", "Generating"
    FAILED = "failed", "Failed"
    READY = "ready", "Ready"


class Song(models.Model):
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="songs")
    gen_form = models.ForeignKey(
        GenForm,
        on_delete=models.SET_NULL,
        related_name="songs",
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    e_rating = models.CharField(max_length=1, blank=True, default="E")
    title = models.CharField(max_length=255)
    audio_url = models.URLField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(e_rating="E") | Q(e_rating=""),
                name="song_e_rating_e_or_blank",
            )
        ]

    def __str__(self) -> str:
        return self.title
