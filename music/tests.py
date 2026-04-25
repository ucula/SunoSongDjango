from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from music.views import GeneratorViewController


class UmlTemplateRouteTests(TestCase):
    def test_login_template_route_renders(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LoginTemplate")

    def test_gen_form_template_route_renders(self):
        response = self.client.get("/generate/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GenFormTemplate")

    def test_library_template_route_renders(self):
        response = self.client.get("/library/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LibraryTemplate")

    def test_song_template_route_renders(self):
        response = self.client.get("/song/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SongTemplate")

    def test_favourite_template_route_renders(self):
        response = self.client.get("/favourite/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FavouriteTemplate")


class SongGenerationStrategyTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            display_name="strategy-user",
            email="strategy-user@example.com",
            password="1234",
        )
        self.gen_form = GeneratorViewController.create_gen_form(
            user=self.user,
            title="Rainwalk",
            mood_tone="Calm",
            genre="Lo-fi",
            voice="female",
            description="Night rain and soft piano",
        )

    def test_mock_strategy_is_deterministic(self):
        first_song = GeneratorViewController.generate_song_for_form(
            self.gen_form.pk,
            strategy_name="mock",
        )
        second_song = GeneratorViewController.generate_song_for_form(
            self.gen_form.pk,
            strategy_name="mock",
        )

        self.assertEqual(first_song.status, "ready")
        self.assertEqual(second_song.status, "ready")
        self.assertEqual(first_song.title, second_song.title)
        self.assertIn("mock-", first_song.title)

    def test_suno_strategy_fails_when_not_configured(self):
        with self.settings(
            SONG_GENERATION_STRATEGY="suno_api",
            SUNO_API_URL="",
            SUNO_API_KEY="",
        ):
            song = GeneratorViewController.generate_song_for_form(self.gen_form.pk)

        self.assertEqual(song.status, "failed")

    @patch("music.views.generator_views.urlopen")
    def test_suno_strategy_success_path(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"title":"API Anthem","e_rating":"E","song_id":"song-123"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with self.settings(
            SUNO_API_URL="https://example.test/suno/generate",
            SUNO_API_KEY="test-key",
            SONG_GENERATION_STRATEGY="suno_api",
        ):
            song = GeneratorViewController.generate_song_for_form(self.gen_form.pk)

        self.assertEqual(song.status, "ready")
        self.assertEqual(song.title, "API Anthem")


class SongGenerationEndpointTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            display_name="endpoint-user",
            email="endpoint-user@example.com",
            password="1234",
        )
        self.gen_form = GeneratorViewController.create_gen_form(
            user=self.user,
            title="Night Drive",
            mood_tone="Dreamy",
            genre="Synthwave",
            voice="male",
            description="Neon lights and midnight roads",
        )

    def test_generate_song_api_mock_strategy(self):
        response = self.client.post(
            f"/generate/song/{self.gen_form.pk}/",
            {"strategy": "mock"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["strategy"], "mock")
        self.assertIn("mock-", payload["title"])

    @patch("music.views.generator_views.urlopen")
    def test_generate_song_api_suno_strategy(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"title":"Suno Endpoint Song","e_rating":"E","song_id":"song-888"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with self.settings(
            SUNO_API_URL="https://example.test/suno/generate",
            SUNO_API_KEY="test-key",
        ):
            response = self.client.post(
                f"/generate/song/{self.gen_form.pk}/",
                data='{"strategy":"suno_api"}',
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["strategy"], "suno_api")
        self.assertEqual(payload["title"], "Suno Endpoint Song")

    def test_generate_song_api_rejects_get(self):
        response = self.client.get(f"/generate/song/{self.gen_form.pk}/")

        self.assertEqual(response.status_code, 405)
