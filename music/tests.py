from unittest.mock import MagicMock, patch
from urllib.parse import urlparse, parse_qs

from django.contrib.auth import get_user_model
from django.test import TestCase

from music.models import Library, Song
from music.views import GeneratorViewController, UserViewController


class UmlTemplateRouteTests(TestCase):
    def test_root_route_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SunoSong")

    def test_login_template_route_renders(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SunoSong")

    def test_gen_form_template_redirects_when_not_logged_in(self):
        response = self.client.get("/generate/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login/")

    def test_library_template_redirects_when_not_logged_in(self):
        response = self.client.get("/library/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login/")

    def test_song_template_redirects_when_not_logged_in(self):
        response = self.client.get("/song/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login/")

    def test_favourite_template_redirects_when_not_logged_in(self):
        response = self.client.get("/favourite/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login/")


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


class LoginAndTemplateFlowTests(TestCase):
    def test_login_rejects_non_google_email(self):
        response = self.client.post(
            "/login/",
            {
                "display_name": "non-google",
                "email": "user@example.com",
                "password": "1234",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Google account only")

    def test_login_accepts_google_email(self):
        response = self.client.post(
            "/login/",
            {
                "display_name": "google-user",
                "email": "google-user@gmail.com",
                "password": "1234",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/generate/")

    def test_generate_form_post_creates_song(self):
        self.client.post(
            "/login/",
            {
                "display_name": "gen-flow",
                "email": "gen-flow@gmail.com",
                "password": "1234",
            },
        )

        response = self.client.post(
            "/generate/",
            {
                "title": "Client Song",
                "mood_tone": "Warm",
                "genre": "Pop",
                "voice": "female",
                "description": "Client requested an uplifting theme",
                "strategy": "mock",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Generation finished with status: ready")
        self.assertEqual(Song.objects.count(), 1)


class GoogleOAuthFlowTests(TestCase):
    def test_google_login_start_requires_configuration(self):
        with self.settings(
            GOOGLE_OAUTH_CLIENT_ID="",
            GOOGLE_OAUTH_CLIENT_SECRET="",
            GOOGLE_OAUTH_REDIRECT_URI="",
        ):
            response = self.client.get("/login/google/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login/")

    def test_google_login_start_redirects_to_google(self):
        with self.settings(
            GOOGLE_OAUTH_CLIENT_ID="client-id",
            GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
            GOOGLE_OAUTH_REDIRECT_URI="http://127.0.0.1:8000/login/google/callback/",
        ):
            response = self.client.get("/login/google/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("accounts.google.com/o/oauth2/v2/auth", response.headers["Location"])

        parsed = urlparse(response.headers["Location"])
        query = parse_qs(parsed.query)
        self.assertEqual(query["client_id"][0], "client-id")
        self.assertIn("state", query)

        session = self.client.session
        self.assertTrue(session.get("google_oauth_state"))

    @patch.object(UserViewController, "fetch_google_user_profile")
    @patch.object(UserViewController, "exchange_code_for_token")
    def test_google_callback_logs_in_user(self, mock_exchange, mock_profile):
        mock_exchange.return_value = {"access_token": "token-123"}
        mock_profile.return_value = {
            "email": "oauth-user@gmail.com",
            "email_verified": True,
            "name": "OAuth User",
        }

        session = self.client.session
        session["google_oauth_state"] = "good-state"
        session.save()

        response = self.client.get("/login/google/callback/?state=good-state&code=abc123")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/generate/")

        user_model = get_user_model()
        self.assertTrue(user_model.objects.filter(email="oauth-user@gmail.com").exists())
        updated_session = self.client.session
        self.assertTrue(updated_session.get("active_user_id"))

    def test_google_callback_rejects_invalid_state(self):
        session = self.client.session
        session["google_oauth_state"] = "expected-state"
        session.save()

        response = self.client.get("/login/google/callback/?state=wrong-state&code=abc123")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login/")


class LibraryFeatureEndpointTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            display_name="library-user",
            email="library-user@gmail.com",
            password="1234",
        )
        self.library, _ = Library.objects.get_or_create(user=self.user)
        self.song = Song.objects.create(
            library=self.library,
            title="Downloadable Song",
            status="ready",
            e_rating="E",
            audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        )

        session = self.client.session
        session["active_user_id"] = self.user.pk
        session.save()

    def test_song_share_api_returns_payload(self):
        response = self.client.get(f"/song/{self.song.pk}/share/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], self.song.title)
        self.assertIn("/song/?song_id=", payload["share_path"])

    def test_song_download_txt(self):
        response = self.client.get(f"/song/{self.song.pk}/download/?format=txt")

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment; filename=\"song_", response.headers["Content-Disposition"])
        self.assertContains(response, "Downloadable Song")
