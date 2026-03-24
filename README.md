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