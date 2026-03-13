# Architecture

## Overview

Habit Tracker is a monolithic Django application. It serves a server-rendered single-page frontend from Django templates and exposes a JSON REST API consumed by that same frontend. All business logic lives in the `habits` Django app.

```
Browser
  │
  ├── GET /            →  Django TemplateView (index.html)
  ├── GET /login/      →  Django TemplateView (login.html)
  └── /api/v1/...      →  Django REST Framework views
                              │
                         habits app
                         ├── models.py        (data layer)
                         ├── serializers.py   (validation + shape)
                         ├── views/           (HTTP handlers)
                         └── services/        (business logic)
                                │
                           PostgreSQL
```

## Directory Structure

```
habit-tracker/
├── config/                  # Django project config (settings, urls, wsgi)
├── habits/
│   ├── migrations/          # Database migrations
│   ├── services/
│   │   ├── period.py        # Period key generation and bounds computation
│   │   └── streak.py        # Streak and analytics computation
│   ├── views/
│   │   ├── auth.py          # Register, login, logout, me
│   │   ├── habits.py        # HabitViewSet, CompletionViewSet
│   │   └── analytics.py     # Summary and CSV/JSON export
│   ├── static/habits/       # CSS and JS served by Django
│   ├── templates/habits/    # base.html, index.html, login.html
│   ├── models.py
│   ├── serializers.py
│   ├── managers.py
│   ├── urls.py
│   └── tests/
│       ├── factories.py
│       ├── test_api.py
│       ├── test_period.py
│       └── test_streak.py
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Data Model

### `User`
Extends Django's `AbstractUser`. Adds a unique `email` field. Used as the `AUTH_USER_MODEL`.

### `Habit`
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key, non-editable |
| `user` | FK → User | Owner; cascade delete |
| `task_specification` | CharField(255) | The habit description |
| `periodicity` | CharField (enum) | `DAILY`, `WEEKLY`, or `MONTHLY` |
| `is_archived` | Boolean | Soft-delete flag |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-updated on save |

A composite index on `(user, is_archived)` supports the common list query.

### `Completion`
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `habit` | FK → Habit | Cascade delete |
| `completed_at` | DateTimeField | Defaults to `now()` |
| `period_key` | CharField(20) | Canonical period string (see below) |
| `note` | TextField | Optional free text |

`period_key` is indexed and acts as the canonical period identifier. It is set automatically on creation and never changes. Examples: `2024-06-15` (daily), `2024-W23` (weekly, ISO 8601), `2024-06` (monthly).

## Services Layer

Business logic is kept out of models and views and lives in `habits/services/`.

### `services/period.py`

Three pure functions, all timezone-aware (UTC throughout):

- **`get_period_key(dt, periodicity) → str`** — returns the canonical key for the period containing `dt`.
- **`get_period_bounds(dt, periodicity) → (start, end)`** — returns the inclusive UTC start/end datetimes for the period.
- **`generate_periods(start_dt, end_dt, periodicity) → list[dict]`** — enumerates every period between two datetimes. Each dict contains `key`, `start`, and `end`.

### `services/streak.py`

**`compute_streak(habit, completion_counts=None) → dict`**

Builds a complete period history from `habit.created_at` to `now`, labels each period as `COMPLETED`, `ACTIVE` (current open period), or `FAILED`, then derives:

- `current_streak` — consecutive completed periods counting back from the most recent non-active period.
- `longest_streak` — maximum consecutive completed periods across all time.
- `completion_rate` — percentage of closed (non-active) periods that were completed.
- `total_completed`, `total_failed`, `total_active` — raw counts.
- `periods` — the full labelled history, newest first.

The optional `completion_counts` parameter accepts a pre-fetched `{period_key: count}` dict, allowing the summary endpoint to avoid N+1 queries by bulk-fetching completions before iterating habits.

## API Design

### Authentication
Session-based authentication using Django's built-in session framework. The frontend reads the `csrftoken` cookie and sends it as `X-CSRFToken` on mutating requests.

### ViewSets
`HabitViewSet` uses DRF's `ModelViewSet`. Two custom `@action` decorators extend it:
- `archive` / `unarchive` — toggle `is_archived` without allowing `periodicity` changes via the standard `update` path (the serializer's `update()` silently strips `periodicity`).
- `analytics` — returns the period history, optionally filtered by `?start=` and `?end=` date query params.

`CompletionViewSet` uses only `CreateModelMixin` and `DestroyModelMixin`. The habit lookup is scoped to `request.user` via `get_habit()`, so attempting to complete another user's habit yields 404.

### Serializers
- `HabitSerializer` — list and create responses.
- `HabitDetailSerializer` — adds `current_streak`, `longest_streak`, `completion_rate`, and `is_broken` via `SerializerMethodField`. Caches the analytics call per object to avoid duplicate computation when the same habit appears more than once.
- `CompletionSerializer` — automatically sets `period_key` from `completed_at` on creation.

### Analytics Endpoints
- **`/api/v1/analytics/summary/`** — aggregates streak/broken status across all of the user's habits. Uses a single bulk DB query for completion counts to avoid N+1 queries, then calls `habit.get_analytics_for_counts(pre_fetched_counts)`.
- **`/api/v1/analytics/export/`** — streams CSV via `StreamingHttpResponse` (no memory spike for large datasets), or returns JSON via the standard `Response`.

## Frontend Architecture

The frontend is a minimal single-page application served from Django templates with no build step.

- **`state.js`** — a plain JS object (`state`) with a `setState(partial)` function that merges changes and calls `render()`.
- **`api.js`** — a thin fetch wrapper (`apiFetch`) plus domain-specific modules (`auth`, `habits`, `completions`, `analytics`). Handles CSRF token injection and redirects to `/login/` on 401/403.
- **`app.js`** — all render functions and event handlers. Renders are synchronous string-based HTML interpolation with explicit XSS protection via `escapeHtml()`.

The UI uses TailwindCSS (CDN, no compilation) and Particles.js for the background animation.

## Key Design Decisions

**Period keys as denormalized strings.** Storing `period_key` on `Completion` rather than computing it at query time allows simple, indexed lookups without timezone-aware date arithmetic in SQL. The trade-off is that the key must be correct at write time — enforced by `CompletionSerializer.create()`.

**No per-request streak computation on list endpoints.** The `GET /habits/` list returns `HabitSerializer` (no analytics fields) to keep list queries fast. Analytics are only computed on `retrieve`, `analytics`, `summary`, and `export`.

**Soft-archiving over hard deletion.** `is_archived` is a flag rather than a delete. The `HabitManager.for_user()` method filters by it, and `HabitViewSet.get_queryset()` always includes archived records so that `unarchive` and other detail actions resolve correctly regardless of query params.

**Services receive pre-fetched data for bulk paths.** `compute_streak` accepts an optional `completion_counts` dict so the summary endpoint can batch-load all completion data in a single query and pass it in, rather than letting each habit trigger its own DB query.