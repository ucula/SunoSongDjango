from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from music.models import GenForm, Library, Song, Status, User, Voice


DEFAULT_AUDIO_URL = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"


class SongGenerationError(Exception):
	"""Raised when a generation strategy cannot produce a song."""


@dataclass(frozen=True)
class GenerationPayload:
	title: str
	mood_tone: str
	genre: str
	voice: str
	description: str

	@classmethod
	def from_gen_form(cls, gen_form):
		return cls(
			title=gen_form.title,
			mood_tone=gen_form.mood_tone,
			genre=gen_form.genre,
			voice=gen_form.voice,
			description=gen_form.description,
		)


@dataclass(frozen=True)
class GenerationResult:
	title: str | None = None
	e_rating: str = "E"
	external_id: str | None = None
	audio_url: str = DEFAULT_AUDIO_URL


class SongGenerationStrategy(ABC):
	key: str

	@abstractmethod
	def generate(self, payload: GenerationPayload) -> GenerationResult:
		raise NotImplementedError


class MockSongGenerationStrategy(SongGenerationStrategy):
	key = "mock"

	def generate(self, payload: GenerationPayload) -> GenerationResult:
		source = "|".join(
			[
				payload.title,
				payload.mood_tone,
				payload.genre,
				payload.voice,
				payload.description,
			]
		)
		digest = sha256(source.encode("utf-8")).hexdigest()[:12]
		return GenerationResult(
			title=f"{payload.title} [mock-{digest[:6]}]",
			e_rating="E",
			external_id=f"mock-{digest}",
			audio_url=DEFAULT_AUDIO_URL,
		)



class SunoApiOrgGenerationStrategy(SongGenerationStrategy):
	key = "api"

	def __init__(self, *, base_url: str, api_key: str, timeout_seconds: int = 15):
		self.base_url = base_url.strip().rstrip("/")
		self.api_key = api_key.strip()
		self.timeout_seconds = timeout_seconds

	def generate(self, payload: GenerationPayload) -> GenerationResult:
		if not self.base_url:
			raise SongGenerationError("SUNO_API_URL is not configured.")
		if not self.api_key:
			raise SongGenerationError("SUNO_API_KEY is not configured.")

		# Construct prompt from genre, mood, voice, and topic (description). 
		prompt_parts = []
		if payload.genre:
			prompt_parts.append(f"Genre: {payload.genre}")
		if payload.mood_tone:
			prompt_parts.append(f"Mood: {payload.mood_tone}")
		if payload.voice:
			prompt_parts.append(f"Vocals: {payload.voice}")
		if payload.description:
			prompt_parts.append(f"Topic: {payload.description}")
			
		prompt_text = ", ".join(prompt_parts) or "A creative song"

		request_body = {
			"customMode": False,
			"instrumental": False,
			"model": "V4_5ALL",
			"callBackUrl": "https://api.sunoapi.org/dummy-callback",
			"prompt": prompt_text[:490]
		}
		
		encoded_body = json.dumps(request_body).encode("utf-8")
		request = Request(
			url=f"{self.base_url}/api/v1/generate",
			data=encoded_body,
			headers={
				"Content-Type": "application/json",
				"Authorization": f"Bearer {self.api_key}",
				"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
			},
			method="POST",
		)

		try:
			with urlopen(request, timeout=self.timeout_seconds) as response:
				raw_response = response.read().decode("utf-8") or "{}"
		except HTTPError as exc:
			raise SongGenerationError(f"sunoapi.org API POST returned HTTP {exc.code}.") from exc
		except URLError as exc:
			raise SongGenerationError(f"Could not reach sunoapi.org API: {exc.reason}") from exc

		try:
			payload_data = json.loads(raw_response)
		except json.JSONDecodeError as exc:
			raise SongGenerationError("sunoapi.org API returned malformed JSON.") from exc

		if payload_data.get("code") != 200:
			raise SongGenerationError(f"API Error: {payload_data.get('msg', 'Unknown')}")
			
		task_data = payload_data.get("data", {})
		task_id = task_data.get("taskId")
		
		if not task_id:
			raise SongGenerationError("API did not return a taskId.")

		# 2. Poll for Status
		max_attempts = 30  # Max 30 attempts * 5s = 150 seconds
		for attempt in range(max_attempts):
			time.sleep(5) # Wait 5 seconds between polls
			
			poll_request = Request(
				url=f"{self.base_url}/api/v1/generate/record-info?taskId={task_id}",
				headers={
					"Authorization": f"Bearer {self.api_key}",
					"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
				},
				method="GET",
			)
			
			try:
				with urlopen(poll_request, timeout=self.timeout_seconds) as poll_response:
					poll_raw = poll_response.read().decode("utf-8") or "{}"
					poll_data = json.loads(poll_raw)
			except Exception as exc:
				print(f"Polling error: {exc}")
				continue # Retry on transient network errors
				
			if poll_data.get("code") != 200:
				continue
				
			status_data = poll_data.get("data", {})
			status = status_data.get("status")
			
			if status == "SUCCESS":
				# Extract audio URL
				response_obj = status_data.get("response", {})
				data_list = response_obj.get("sunoData", [])
				if data_list and isinstance(data_list, list) and len(data_list) > 0:
					audio_url = data_list[0].get("audioUrl") or DEFAULT_AUDIO_URL
				else:
					audio_url = DEFAULT_AUDIO_URL
					
				return GenerationResult(
					title=payload.title,
					e_rating="E",
					external_id=task_id,
					audio_url=audio_url,
				)
			elif status and "FAILED" in status:
				raise SongGenerationError(f"sunoapi.org generation failed: {status}")
				
		raise SongGenerationError("Timed out waiting for sunoapi.org generation.")


def get_generation_strategy(
	strategy_name: str,
	*,
	suno_base_url: str = "",
	suno_api_key: str = "",
	suno_timeout_seconds: int = 10,
) -> SongGenerationStrategy:
	# Hard-coded strategy selector required by the exercise.
	normalized_name = (strategy_name or MockSongGenerationStrategy.key).lower()
	if normalized_name == MockSongGenerationStrategy.key:
		return MockSongGenerationStrategy()
	if normalized_name == SunoApiOrgGenerationStrategy.key:
		return SunoApiOrgGenerationStrategy(
			base_url=suno_base_url,
			api_key=suno_api_key,
			timeout_seconds=suno_timeout_seconds,
		)
	raise ValueError(f"Unsupported song generation strategy: {strategy_name}")


class GeneratorViewController:
	@staticmethod
	def get_active_user(request):
		user_id = request.session.get("active_user_id")
		if not user_id:
			return None
		try:
			return User.objects.get(pk=user_id)
		except User.DoesNotExist:
			return None

	@staticmethod
	def gen_form_template_view(request):
		active_user = GeneratorViewController.get_active_user(request)
		show_tutorial = not request.session.get("gen_tutorial_seen", False)
		if show_tutorial:
			request.session["gen_tutorial_seen"] = True

		context = {
			"active_user": active_user,
			"voice_choices": Voice.choices,
			"strategy_default": getattr(settings, "SONG_GENERATION_STRATEGY", "mock"),
			"show_tutorial": show_tutorial,
			"free_mode_note": "This app is free to use. Mock strategy works without paid API access.",
		}

		if request.method != "POST":
			if active_user is None:
				return HttpResponseRedirect("/login/")
			return render(request, "music/GenFormTemplate.html", context)

		if active_user is None:
			messages.error(request, "Please login with a Google account before generating songs.")
			return render(request, "music/GenFormTemplate.html", context, status=400)

		title = request.POST.get("title", "").strip()
		mood_tone = request.POST.get("mood_tone", "").strip()
		genre = request.POST.get("genre", "").strip()
		voice = request.POST.get("voice", "").strip()
		description = request.POST.get("description", "").strip()
		strategy_name = request.POST.get("strategy", "").strip() or None

		if not all([title, mood_tone, genre, voice]):
			messages.error(request, "Title, Mood, Genre, and Voice are required for generation.")
			context["form_data"] = request.POST
			return render(request, "music/GenFormTemplate.html", context, status=400)

		gen_form = GeneratorViewController.create_gen_form(
			user=active_user,
			title=title,
			mood_tone=mood_tone,
			genre=genre,
			voice=voice,
			description=description,
		)

		try:
			song = GeneratorViewController.generate_song_for_form(gen_form.pk, strategy_name=strategy_name)
		except ValueError as exc:
			messages.error(request, str(exc))
			context["form_data"] = request.POST
			return render(request, "music/GenFormTemplate.html", context, status=400)

		messages.success(request, f"Generation started! Check your Library to view the song status.")
		return HttpResponseRedirect("/library/")

	@staticmethod
	def resolve_generation_strategy(strategy_name=None):
		selected_strategy = strategy_name or getattr(settings, "SONG_GENERATION_STRATEGY", "mock")
		return get_generation_strategy(
			selected_strategy,
			suno_base_url=getattr(settings, "SUNO_API_URL", ""),
			suno_api_key=getattr(settings, "SUNO_API_KEY", ""),
			suno_timeout_seconds=getattr(settings, "SUNO_API_TIMEOUT_SECONDS", 10),
		)

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
			audio_url=DEFAULT_AUDIO_URL,
		)
		return song

	@staticmethod
	def generate_song_for_form(gen_form_id, *, strategy_name=None):
		gen_form = GenForm.objects.select_related("user").get(pk=gen_form_id)
		song = GeneratorViewController.start_generation(gen_form_id, song_title=gen_form.title, e_rating="E")
		strategy = GeneratorViewController.resolve_generation_strategy(strategy_name)
		payload = GenerationPayload.from_gen_form(gen_form)

		try:
			generation_result = strategy.generate(payload)
		except SongGenerationError as exc:
			print(f"Generation failed: {exc}")
			# We'll pass the error message up so it can be shown to the user
			song.status = Status.FAILED
			song.save(update_fields=["status"])
			raise ValueError(f"Generation failed: {str(exc)}") from exc

		fields_to_update = []
		if generation_result.title and generation_result.title != song.title:
			song.title = generation_result.title
			fields_to_update.append("title")
		if generation_result.e_rating in {"E", ""} and generation_result.e_rating != song.e_rating:
			song.e_rating = generation_result.e_rating
			fields_to_update.append("e_rating")
		if generation_result.audio_url and generation_result.audio_url != song.audio_url:
			song.audio_url = generation_result.audio_url
			fields_to_update.append("audio_url")

		if fields_to_update:
			song.save(update_fields=fields_to_update)

		return GeneratorViewController.mark_ready(song.pk)

	@staticmethod
	def generate_song_api_view(request, gen_form_id):
		if request.method != "POST":
			return JsonResponse({"detail": "Method not allowed. Use POST."}, status=405)

		strategy_name = request.POST.get("strategy")
		if request.content_type and "application/json" in request.content_type:
			try:
				parsed_payload = json.loads(request.body.decode("utf-8") or "{}")
			except json.JSONDecodeError:
				return JsonResponse({"detail": "Invalid JSON body."}, status=400)
			strategy_name = parsed_payload.get("strategy", strategy_name)

		try:
			song = GeneratorViewController.generate_song_for_form(gen_form_id, strategy_name=strategy_name)
		except GenForm.DoesNotExist:
			return JsonResponse({"detail": "GenForm not found."}, status=404)
		except ValueError as exc:
			return JsonResponse({"detail": str(exc)}, status=400)

		selected_strategy = strategy_name or getattr(settings, "SONG_GENERATION_STRATEGY", "mock")
		return JsonResponse(
			{
				"song_id": song.pk,
				"title": song.title,
				"status": song.status,
				"strategy": selected_strategy,
			}
		)

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
