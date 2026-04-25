from django.db import transaction
from django.shortcuts import render

from music.models import GenForm, Library, Song, Status


class GeneratorViewController:
	@staticmethod
	def gen_form_template_view(request):
		return render(request, "music/GenFormTemplate.html")

	@staticmethod
	@transaction.atomic
	def create_gen_form(*, user, title, mood_tone, genre, voice, description):
		gen_form = GenForm.objects.create(
			user=user,
			title=title,
			mood_tone=mood_tone,
			genre=genre,
			voice=voice,
			description=description,
		)
		return gen_form

	@staticmethod
	@transaction.atomic
	def start_generation(gen_form_id, *, song_title=None, e_rating="E"):
		gen_form = GenForm.objects.select_related("user").get(pk=gen_form_id)
		library, _ = Library.objects.get_or_create(user=gen_form.user)
		song = Song.objects.create(
			library=library,
			gen_form=gen_form,
			title=song_title or gen_form.title,
			status=Status.GENERATING,
			e_rating=e_rating,
		)
		return song

	@staticmethod
	@transaction.atomic
	def mark_ready(song_id):
		song = Song.objects.get(pk=song_id)
		song.status = Status.READY
		song.save(update_fields=["status"])
		return song

	@staticmethod
	@transaction.atomic
	def mark_failed(song_id):
		song = Song.objects.get(pk=song_id)
		song.status = Status.FAILED
		song.save(update_fields=["status"])
		return song
