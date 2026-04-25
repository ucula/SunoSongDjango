from django.db import models

from .library import Library
from .song import Song


class Favourite(models.Model):
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="favorites")
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="favorited_in")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "song"],
                name="unique_favorite_per_library_song",
            )
        ]

    def __str__(self) -> str:
        return f"Favourite: {self.song}"
