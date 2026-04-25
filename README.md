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

The generation flow now uses interchangeable strategies so domain logic can stay unchanged while generation behavior changes.

- `mock`: deterministic, offline generator for local development/tests.
- `suno_api`: external API-backed generator.

### Configuration

Set these values with environment variables. They are read in `config/settings.py`:

- `SONG_GENERATION_STRATEGY` (default: `mock`)
- `SUNO_API_URL` (required for `suno_api`)
- `SUNO_API_KEY` (required for `suno_api`)
- `SUNO_API_TIMEOUT_SECONDS` (default: `10`)

Example:

```bash
export SONG_GENERATION_STRATEGY=mock
export SUNO_API_URL=https://your-suno-endpoint.example/api/generate
export SUNO_API_KEY=your_real_suno_api_key
export SUNO_API_TIMEOUT_SECONDS=10
```

### How to switch strategy

1. Set `SONG_GENERATION_STRATEGY=mock` for deterministic offline mode.
2. Set `SONG_GENERATION_STRATEGY=suno_api` to use the Suno API strategy.
3. Restart the Django server after changing environment variables.

The strategy selector is intentionally hard-coded in `get_generation_strategy(...)` to the supported values `mock` and `suno_api`.

### Where to put the SUNO API key

Put the key in the `SUNO_API_KEY` environment variable before starting Django.

- macOS/Linux shell: `export SUNO_API_KEY=...`
- Then run: `python manage.py runserver`

### Usage in code

Use `GeneratorViewController.generate_song_for_form(gen_form_id, strategy_name=None)`.

- If `strategy_name` is provided, it overrides configured default.
- If omitted, the controller uses `SONG_GENERATION_STRATEGY`.

### Backend endpoint

POST endpoint for generation:

- `POST /generate/song/<gen_form_id>/`
- Optional body field: `strategy` (`mock` or `suno_api`)

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