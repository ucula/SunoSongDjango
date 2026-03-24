from django.db import transaction

from music.models import Favorite, Library, Song, Status


class SongController:
	@staticmethod
	@transaction.atomic
	def create_song(*, library_id, title, status=Status.GENERATING, e_rating="E", gen_form=None):
		library = Library.objects.get(pk=library_id)
		song = Song.objects.create(
			library=library,
			title=title,
			status=status,
			e_rating=e_rating,
			gen_form=gen_form,
		)
		return song

	@staticmethod
	def get_song(song_id):
		return Song.objects.select_related("library", "library__user", "gen_form").get(pk=song_id)

	@staticmethod
	def list_songs_for_library(library_id):
		return Song.objects.filter(library_id=library_id).select_related("library", "gen_form").order_by("-timestamp")

	@staticmethod
	@transaction.atomic
	def update_song(song_id, **updates):
		song = Song.objects.get(pk=song_id)
		for field, value in updates.items():
			if hasattr(song, field):
				setattr(song, field, value)
		song.save()
		return song

	@staticmethod
	@transaction.atomic
	def delete_song(song_id):
		song = Song.objects.get(pk=song_id)
		song.delete()
		return True

	@staticmethod
	@transaction.atomic
	def add_favorite(library_id, song_id):
		favorite, _ = Favorite.objects.get_or_create(library_id=library_id, song_id=song_id)
		return favorite

	@staticmethod
	@transaction.atomic
	def remove_favorite(library_id, song_id):
		Favorite.objects.filter(library_id=library_id, song_id=song_id).delete()
		return True
