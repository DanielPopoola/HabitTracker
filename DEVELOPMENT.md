# Development Guide

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [uv](https://docs.astral.sh/uv/) (optional — only needed for running things outside Docker)

## Initial Setup

```bash
git clone <repo-url>
cd habit-tracker

cp .env.example .env
# Edit .env and fill in values (see Environment Variables below)

docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

The app runs at [http://localhost:8000](http://localhost:8000).

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | any long random string |
| `DEBUG` | Enable debug mode | `True` |
| `DB_NAME` | Postgres database name | `habit_tracker` |
| `DB_USER` | Postgres username | `postgres` |
| `DB_PASSWORD` | Postgres password | `postgres` |
| `DB_HOST` | Postgres hostname | `db` (Docker service name) |
| `DB_PORT` | Postgres port | `5432` |

## Common Commands

All commands run inside the `web` container:

```bash
# Run the dev server (already done by docker compose up)
docker compose exec web python manage.py runserver 0.0.0.0:8000

# Apply migrations
docker compose exec web python manage.py migrate

# Create a new migration after changing models
docker compose exec web python manage.py makemigrations

# Open a Django shell
docker compose exec web python manage.py shell

# Connect to Postgres directly
docker compose exec db psql -U $DB_USER -d $DB_NAME
```

## Running Tests

```bash
# Run the full test suite
docker compose exec web pytest

# Run only a specific test file
docker compose exec web pytest habits/tests/test_streak.py

# Run a specific test
docker compose exec web pytest habits/tests/test_api.py::TestHabitEndpoints::test_create_habit

# Run with verbose output
docker compose exec web pytest -v

# Run with stdout (useful for debugging)
docker compose exec web pytest -s
```

Tests are organized into three files:

| File | What it covers |
|------|---------------|
| `test_period.py` | Pure unit tests for `period.py` service (bounds, keys, generation) |
| `test_streak.py` | Unit tests for `streak.py` service (current/longest streak, completion rate) |
| `test_api.py` | Integration tests for all HTTP endpoints (habits, completions, analytics) |

All tests use `pytest-django` and `factory-boy`. No mocking of the database — tests run against a real Postgres instance via Docker.

## Project Layout

```
habits/
├── models.py          # User, Habit, Completion
├── managers.py        # HabitManager, CompletionManager (scoped querysets)
├── serializers.py     # DRF serializers for all models + analytics
├── urls.py            # URL routing for the habits app
├── admin.py           # Admin registrations
├── views/
│   ├── __init__.py    # Re-exports all views
│   ├── auth.py        # Register, login, logout, me
│   ├── habits.py      # HabitViewSet, CompletionViewSet
│   └── analytics.py   # AnalyticsSummaryView, ExportView
├── services/
│   ├── period.py      # Period key + bounds computation (pure functions)
│   └── streak.py      # Streak computation (pure function over periods)
├── templates/habits/
│   ├── base.html      # Shared layout, static assets
│   ├── index.html     # Dashboard
│   └── login.html     # Login/register
├── static/habits/
│   ├── css/styles.css
│   └── js/
│       ├── api.js     # Fetch wrapper + domain API modules
│       ├── state.js   # Global state object + setState()
│       └── app.js     # Render functions + event handlers
└── tests/
    ├── factories.py
    ├── test_api.py
    ├── test_period.py
    └── test_streak.py
```

## Making Changes

### Adding a new field to a model

1. Edit `habits/models.py`.
2. Run `docker compose exec web python manage.py makemigrations`.
3. Run `docker compose exec web python manage.py migrate`.
4. Update the relevant serializer in `habits/serializers.py` if the field should be exposed.

### Adding a new endpoint

1. Add a view in the appropriate file under `habits/views/`.
2. Register it in `habits/urls.py`.
3. Export it from `habits/views/__init__.py` if needed.
4. Write an integration test in `habits/tests/test_api.py`.

### Adding business logic

Keep it in `habits/services/`. Services are plain Python functions — no Django imports unless necessary, no side effects beyond what's explicitly documented. This makes them easy to unit test in isolation.

### Changing the frontend

The frontend has no build step. Edit the files in `habits/static/habits/` and `habits/templates/habits/` directly. Because Django serves static files from the `static/` directories in development, changes are picked up immediately on page reload.

If you add a new JS module, import it in `base.html` in dependency order (currently: `api.js` → `state.js` → `app.js`).

## API Documentation

Interactive Swagger UI is available at [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

The raw OpenAPI schema is at [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/) or in `schema.yml` in the repo root. To regenerate the schema file after changing views or serializers:

```bash
docker compose exec web python manage.py spectacular --file schema.yml
```

## Code Style

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
# Lint
docker compose exec web ruff check .

# Format
docker compose exec web ruff format .
```

Configuration is in `pyproject.toml`. Line length is 105. Imports are auto-sorted. String quotes use single quotes; indentation uses tabs.

## Dependency Management

Dependencies are managed with `uv` and declared in `pyproject.toml`. The `uv.lock` file is committed to the repo for reproducible installs.

```bash
# Add a dependency
uv add <package>

# Remove a dependency
uv remove <package>

# Sync the environment (run inside the container or locally with uv installed)
uv pip install --system -e .
```

After adding or removing dependencies, rebuild the Docker image:

```bash
docker compose up --build
```