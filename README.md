# Habit Tracker

A REST API with a server-rendered frontend for defining, tracking, and analyzing personal habits. Built with Django, Django REST Framework, and PostgreSQL.

## Quick Start

```bash
cp .env.example .env        # fill in values
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

The app is available at [http://localhost:8000](http://localhost:8000).  
API docs (Swagger UI) are at [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

## Running Tests

```bash
docker compose exec web pytest
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register/` | Register a new user |
| `POST` | `/api/v1/auth/login/` | Log in |
| `POST` | `/api/v1/auth/logout/` | Log out |
| `GET` | `/api/v1/auth/me/` | Current user info |
| `GET` | `/api/v1/habits/` | List habits (filter: `?is_archived=true/false`) |
| `POST` | `/api/v1/habits/` | Create a habit |
| `GET` | `/api/v1/habits/:id/` | Retrieve a habit with analytics |
| `PATCH` | `/api/v1/habits/:id/` | Update a habit |
| `DELETE` | `/api/v1/habits/:id/` | Delete a habit |
| `PATCH` | `/api/v1/habits/:id/archive/` | Archive a habit |
| `PATCH` | `/api/v1/habits/:id/unarchive/` | Unarchive a habit |
| `GET` | `/api/v1/habits/:id/analytics/` | Period history (filter: `?start=&end=`) |
| `POST` | `/api/v1/habits/:id/completions/` | Log a completion |
| `DELETE` | `/api/v1/habits/:id/completions/:id/` | Delete a completion |
| `GET` | `/api/v1/analytics/summary/` | Aggregate stats across all habits |
| `GET` | `/api/v1/analytics/export/` | Export data (`?format=csv` or `?format=json`) |

## Tech Stack

- **Backend:** Python 3.12, Django 6, Django REST Framework
- **Database:** PostgreSQL 15
- **Schema docs:** drf-spectacular (OpenAPI 3)
- **Frontend:** Vanilla JS, TailwindCSS (CDN), Particles.js
- **Containerization:** Docker, Docker Compose
- **Package manager:** uv
- **Testing:** pytest, pytest-django, factory-boy

## Further Reading

- [ARCHITECTURE.md](ARCHITECTURE.md) — system design, data model, and key decisions
- [DEVELOPMENT.md](DEVELOPMENT.md) — local setup, workflow, and conventions