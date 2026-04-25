from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Exists, OuterRef

from music.models import Favourite, Library, Song, Status, User

class LibraryViewController:
	@staticmethod
	def _build_library_context(request):
		active_user = None
		user_id = request.session.get("active_user_id")
		if user_id:
			try:
				active_user = User.objects.get(pk=user_id)
			except User.DoesNotExist:
				pass
		
		if not active_user:
			return None

		# Make sure library exists
		library, _ = Library.objects.get_or_create(user=active_user)
		songs = Song.objects.filter(library=library)
		
		# Handle search
		q = request.GET.get("q")
		if q:
			songs = songs.filter(title__icontains=q)
			
		songs = songs.annotate(
			is_favorited=Exists(Favourite.objects.filter(library=library, song=OuterRef("pk")))
		).select_related("gen_form").order_by("-timestamp")
		
		return {
			"active_user": active_user,
			"library": library,
			"songs": songs,
			"q": q or "",
		}

	@staticmethod
	def library_template_view(request):
		context = LibraryViewController._build_library_context(request)
		if not context:
			return HttpResponseRedirect("/login/")
			
		# Handle Delete POST
		if request.method == "POST" and "delete_song_id" in request.POST:
			song_id = request.POST.get("delete_song_id")
			try:
				Song.objects.filter(pk=song_id, library=context["library"]).delete()
			except Exception as e:
				pass
			return redirect("library-template")
			
		# Handle Toggle Favorite POST
		if request.method == "POST" and "toggle_favorite_id" in request.POST:
			song_id = request.POST.get("toggle_favorite_id")
			try:
				song = Song.objects.get(pk=song_id, library=context["library"])
				fav, created = Favourite.objects.get_or_create(library=context["library"], song=song)
				if not created:
					fav.delete()
			except Song.DoesNotExist:
				pass
			return redirect("library-template")
			
		# Handle Edit Prompt POST
		if request.method == "POST" and "edit_prompt" in request.POST:
			song_id = request.POST.get("song_id")
			new_title = request.POST.get("title", "")
			new_mood = request.POST.get("mood_tone", "")
			new_genre = request.POST.get("genre", "")
			new_voice = request.POST.get("voice", "")
			new_desc = request.POST.get("description", "")
			
			try:
				song = Song.objects.get(pk=song_id, library=context["library"])
				if song.gen_form:
					song.gen_form.title = new_title
					song.gen_form.mood_tone = new_mood
					song.gen_form.genre = new_genre
					song.gen_form.voice = new_voice
					song.gen_form.description = new_desc
					song.gen_form.save()
				
				song.status = Status.GENERATING
				song.save()
				
				from music.views.generator_views import GeneratorViewController, GenerationPayload, SongGenerationError
				
				strategy_name = request.POST.get("strategy")
				strategy = GeneratorViewController.resolve_generation_strategy(strategy_name)
				payload = GenerationPayload.from_gen_form(song.gen_form)
				
				try:
					generation_result = strategy.generate(payload)
					if generation_result.title and generation_result.title != song.title:
						song.title = generation_result.title
					if generation_result.e_rating in {"E", ""} and generation_result.e_rating != song.e_rating:
						song.e_rating = generation_result.e_rating
					if generation_result.audio_url and generation_result.audio_url != song.audio_url:
						song.audio_url = generation_result.audio_url
					song.status = Status.READY
					song.save()
				except SongGenerationError as exc:
					song.status = Status.FAILED
					song.save()
					messages.error(request, f"Generation failed: {str(exc)}")
				
			except Song.DoesNotExist:
				messages.error(request, "Song not found.")
			return redirect("library-template")

		return render(request, "music/LibraryTemplate.html", context)

	@staticmethod
	def favourite_template_view(request):
		context = LibraryViewController._build_library_context(request)
		if not context:
			return HttpResponseRedirect("/login/")
			
		# Filter only songs that are favorited
		context["songs"] = context["songs"].filter(is_favorited=True)
		
		return render(request, "music/FavouriteTemplate.html", context)

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
		favorite, _ = Favourite.objects.get_or_create(library_id=library_id, song_id=song_id)
		return favorite

	@staticmethod
	@transaction.atomic
	def remove_favorite(library_id, song_id):
		Favourite.objects.filter(library_id=library_id, song_id=song_id).delete()
		return True

