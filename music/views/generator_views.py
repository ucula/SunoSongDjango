from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render

from music.models import GenForm, Library, Song, Status


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
		)


class SunoApiSongGenerationStrategy(SongGenerationStrategy):
	key = "suno_api"

	def __init__(self, *, base_url: str, api_key: str, timeout_seconds: int = 10):
		self.base_url = base_url
		self.api_key = api_key
		self.timeout_seconds = timeout_seconds

	def generate(self, payload: GenerationPayload) -> GenerationResult:
		if not self.base_url:
			raise SongGenerationError("SUNO_API_URL is not configured.")
		if not self.api_key:
			raise SongGenerationError("SUNO_API_KEY is not configured.")

		request_body = {
			"title": payload.title,
			"mood_tone": payload.mood_tone,
			"genre": payload.genre,
			"voice": payload.voice,
			"description": payload.description,
		}
		encoded_body = json.dumps(request_body).encode("utf-8")
		request = Request(
			url=self.base_url,
			data=encoded_body,
			headers={
				"Content-Type": "application/json",
				"Authorization": f"Bearer {self.api_key}",
			},
			method="POST",
		)

		try:
			with urlopen(request, timeout=self.timeout_seconds) as response:
				raw_response = response.read().decode("utf-8") or "{}"
		except HTTPError as exc:
			detail = ""
			try:
				detail = exc.read().decode("utf-8")
			except Exception:
				detail = ""
			raise SongGenerationError(
				f"Suno API returned HTTP {exc.code}. {detail}".strip()
			) from exc
		except URLError as exc:
			raise SongGenerationError(f"Could not reach Suno API: {exc.reason}") from exc

		try:
			payload_data = json.loads(raw_response)
		except json.JSONDecodeError as exc:
			raise SongGenerationError("Suno API returned malformed JSON.") from exc

		generated_title = payload_data.get("title") or payload.title
		e_rating = payload_data.get("e_rating", "E")
		if e_rating not in {"E", ""}:
			e_rating = "E"

		return GenerationResult(
			title=generated_title,
			e_rating=e_rating,
			external_id=payload_data.get("song_id") or payload_data.get("id"),
		)


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
	if normalized_name == SunoApiSongGenerationStrategy.key:
		return SunoApiSongGenerationStrategy(
			base_url=suno_base_url,
			api_key=suno_api_key,
			timeout_seconds=suno_timeout_seconds,
		)
	raise ValueError(f"Unsupported song generation strategy: {strategy_name}")


class GeneratorViewController:
	@staticmethod
	def gen_form_template_view(request):
		return render(request, "music/GenFormTemplate.html")

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
		except SongGenerationError:
			return GeneratorViewController.mark_failed(song.pk)

		fields_to_update = []
		if generation_result.title and generation_result.title != song.title:
			song.title = generation_result.title
			fields_to_update.append("title")
		if generation_result.e_rating in {"E", ""} and generation_result.e_rating != song.e_rating:
			song.e_rating = generation_result.e_rating
			fields_to_update.append("e_rating")

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
