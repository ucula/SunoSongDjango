from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class Voice(models.TextChoices):
	MALE = "male", "Male"
	FEMALE = "female", "Female"


class Status(models.TextChoices):
	GENERATING = "generating", "Generating"
	FAILED = "failed", "Failed"
	READY = "ready", "Ready"


class Library(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="library")

	def __str__(self) -> str:
		return f"{self.user} library"


class GenForm(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gen_forms")
	title = models.CharField(max_length=255)
	mood_tone = models.CharField(max_length=255)
	genre = models.CharField(max_length=255)
	voice = models.CharField(max_length=10, choices=Voice.choices)
	description = models.TextField()

	def __str__(self) -> str:
		return self.title


class Song(models.Model):
	library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="songs")
	gen_form = models.OneToOneField(
		GenForm,
		on_delete=models.SET_NULL,
		related_name="song",
		null=True,
		blank=True,
	)
	timestamp = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=20, choices=Status.choices)
	e_rating = models.CharField(max_length=1, blank=True, default="E")
	title = models.CharField(max_length=255)

	class Meta:
		constraints = [
			models.CheckConstraint(
				condition=Q(e_rating="E") | Q(e_rating=""),
				name="song_e_rating_e_or_blank",
			)
		]

	def __str__(self) -> str:
		return self.title


class Favorite(models.Model):
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
		return f"Favorite: {self.song}"
