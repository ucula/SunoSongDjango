# boilerplate_project

## Django App Setup

This project uses a custom Django user model and a music domain app.

### Requirements

- Python 3.14+
- Django installed from `requirements.txt`

### 1) Create and activate the virtual environment

If you already have `.venv`, activate it:

```bash
source .venv/bin/activate
```

If you need to create it first:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Apply database migrations

```bash
python manage.py migrate
```

### 4) Create an admin user

This project uses a custom user model where `display_name` is the login field and `email` is optional.

```bash
python manage.py createsuperuser
```

You will be prompted for:
- `display_name`
- `email` if you want to provide one
- `password`

### 5) Start the development server

```bash
python manage.py runserver
```

### 6) Open the admin panel

Visit:

```text
http://127.0.0.1:8000/admin/
```

### What you can manage in admin

- User: `User ID`, `Display name`, `Email`
- Gen-form: `Title`, `Mood/Tone`, `Genre`, `Voice`, `Description`
- Song: `Timestamp`, `Status`, `E-rating`, `Title`

### Notes

- If you change models, run `python manage.py makemigrations` and then `python manage.py migrate`.
- The project uses the `config` package for settings and URLs.

## Song Generation Strategies (Strategy Pattern)

The generation flow uses the Strategy Pattern to allow interchangeable generation logic. This keeps the core domain logic decoupled from the specific generation implementation.

- `mock`: Deterministic, offline generator for local development and testing.
- `suno`: External API-backed generator using the Suno AI service.

### Configuration

Configuration is managed via environment variables. See [.env.example](file:///.env.example) for a template.

- `GENERATOR_STRATEGY`: Set to `mock` or `suno` (default: `mock`).
- `SUNO_API_URL`: The endpoint URL for the Suno API (required for `suno`).
- `SUNO_API_KEY`: Your API key for Suno (required for `suno`).
- `SUNO_API_TIMEOUT_SECONDS`: Request timeout in seconds (default: `15`).

### How to Switch Strategy

1.  **Mock Mode:** Set `GENERATOR_STRATEGY=mock` in your `.env` file for fast, offline development.
2.  **Live Mode:** Set `GENERATOR_STRATEGY=suno` and provide valid `SUNO_API_URL` and `SUNO_API_KEY` to generate real songs.

The strategy is resolved at runtime in `music/views/generator_views.py` using the `get_generation_strategy` factory function.

### Backend Endpoint

The generation can be triggered via a POST request:

- `POST /generate/song/<gen_form_id>/`
- Body (JSON or Form): `{"strategy": "suno"}` or `{"strategy": "mock"}`

Example using `curl`:

```bash
curl -X POST http://127.0.0.1:8000/generate/song/1/ -d "strategy=suno"
```

### Verification & Tests

Both strategies are covered by automated tests to ensure reliability:

- `SongGenerationStrategyTests`: Verifies individual strategy logic.
- `SongGenerationEndpointTests`: Verifies the API endpoint behavior with different strategies.

Run tests with:
```bash
python manage.py test
```

### Demonstration (unit tests)

The following tests demonstrate both strategies and backend operation:

- `SongGenerationStrategyTests.test_mock_strategy_is_deterministic`
- `SongGenerationStrategyTests.test_suno_strategy_success_path`
- `SongGenerationEndpointTests.test_generate_song_api_mock_strategy`
- `SongGenerationEndpointTests.test_generate_song_api_suno_strategy`

Run all tests:

```bash
python manage.py test
```

## Client Requirement Coverage

This web app currently includes the following features requested by the client:

- Google email only login flow (`@gmail.com`) via LoginTemplate.
- Generation form with required fields: title, mood/tone, genre, singer voice, description.
- Generation statuses (`generating`, `ready`, `failed`) and generation timestamp history in LibraryTemplate.
- Song rating fixed to `E`.
- First-time tutorial hints in generate and library pages.
- Browser playback controls: play, pause, stop, rewind 10s, forward 10s, loop.
- Song search by title.
- Favorites support.
- Download support (txt, json, m3u formats).
- Share API endpoint returning share path and audio URL.
- Prompt editing for generated song metadata (genre/mood/description) and song deletion.
- Desktop-friendly monochrome layout.

## Quick User Flow

1. Open `/login/` and sign in with a Gmail account.
2. Open `/generate/`, fill the form, and submit.
3. Open `/library/` to search, play, favorite, edit prompt, share, or download songs.
4. Open `/favourite/` or `/song/` for dedicated playback/favorites views.