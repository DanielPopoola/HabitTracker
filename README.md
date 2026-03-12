# Habit Tracker

A REST API for defining, tracking, and analyzing personal habits.

## Setup

cp .env.example .env  # fill in values
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

## Running tests

docker compose exec web pytest

## API Docs

http://localhost:8000/api/docs/

## Endpoints

POST   /api/v1/habits/
GET    /api/v1/habits/
GET    /api/v1/habits/:id/
PATCH  /api/v1/habits/:id/
DELETE /api/v1/habits/:id/
PATCH  /api/v1/habits/:id/archive/
GET    /api/v1/habits/:id/analytics/
POST   /api/v1/habits/:id/completions/
DELETE /api/v1/habits/:id/completions/:id/
GET    /api/v1/analytics/summary/
GET    /api/v1/analytics/export/