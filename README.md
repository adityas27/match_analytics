# Football Intelligence Backend

Backend infrastructure for a Football Analytics application. This phase provides
the Django platform, PostgreSQL configuration, API authentication, and testing
foundation. Football domain models and StatsBomb ingestion will be added later.

## Technology stack

- Python 3.13+
- Django
- Django REST Framework
- PostgreSQL with `psycopg2-binary`
- SimpleJWT
- django-cors-headers and django-environ
- uv, pytest, pytest-django, and Ruff

## Prerequisites

Install Python 3.13+, PostgreSQL, and [uv](https://docs.astral.sh/uv/).

On Windows, install uv with:

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

## Setup with uv

From the repository root:

```powershell
uv sync
```

`uv sync` creates or updates the project virtual environment from
`pyproject.toml` and `uv.lock`. Run Python tools through uv:

```powershell
uv run python --version
uv run python manage.py check
```

## PostgreSQL

Create a database and user (or use an existing local PostgreSQL role):

```sql
CREATE USER football_user WITH PASSWORD 'replace-with-a-local-password';
CREATE DATABASE football_db OWNER football_user;
```

Copy `.env.example` to `.env` and set `DATABASE_NAME`, `DATABASE_USER`,
`DATABASE_PASSWORD`, `DATABASE_HOST`, and `DATABASE_PORT` to match PostgreSQL.
`.env` is ignored by git and must never be committed.

## Environment configuration

```powershell
Copy-Item .env.example .env
```

Set a long, unique `SECRET_KEY` and adjust `DEBUG`, `ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS`, and JWT lifetimes for your environment. UTC is used
internally by Django.

## Migrations

Apply migrations:

```powershell
uv run python manage.py migrate
```

When application models change:

```powershell
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## Development server and admin

```powershell
uv run python manage.py runserver
```

The admin is available at `http://127.0.0.1:8000/admin/`. Create an admin user
with `uv run python manage.py createsuperuser`.

## Authentication API

All endpoints are under the versioned `/api/v1/auth/` prefix:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/register/` | Register a user and return access/refresh tokens |
| POST | `/login/` | Obtain access/refresh tokens with email and password |
| POST | `/token/refresh/` | Obtain a new access token |
| POST | `/token/verify/` | Verify a token |
| POST | `/logout/` | Blacklist a refresh token |
| GET | `/me/` | Return the authenticated user's safe profile |

Passwords are hashed by Django and are never returned by the API.

## Tests and linting

```powershell
uv run pytest
uv run ruff check .
```

## Ingestion operations

Ingestion is never started by migrations, application startup, or tests. Every
operation below is an explicit command and must be run manually. The commands
do not delete or truncate records. Existing records are skipped by default;
`--force` is an explicit reprocessing option.

The `--root` value must point to the StatsBomb JSON directory containing
`competitions.json`, `matches/`, `events/`, `lineups/`, and optionally
`three-sixty/` (for this repository, that is `data/data`).

Inspect available files without database writes:

```powershell
uv run python manage.py inspect_dataset --root data/data
```

Estimate a selected workload without importing:

```powershell
uv run python manage.py ingest_dataset --root data/data --dataset competitions --dry-run
uv run python manage.py import_match --root data/data --match-id 15946 --dry-run
```

Import one match and its available events, lineups, and 360 frames:

```powershell
uv run python manage.py import_match --root data/data --match-id 15946
```

Import a selected dataset:

```powershell
uv run python manage.py ingest_dataset --root data/data --dataset competitions
uv run python manage.py ingest_dataset --root data/data --dataset matches
uv run python manage.py ingest_dataset --root data/data --dataset events
uv run python manage.py ingest_dataset --root data/data --dataset lineups
uv run python manage.py ingest_dataset --root data/data --dataset three-sixty
```

The `matches` dataset is stored by competition and season, with multiple match
objects in each JSON array. The command streams each array and imports every
match object; the filename is not treated as a match ID.

Resume a failed dataset run from its last checkpoint:

```powershell
uv run python manage.py ingest_dataset --root data/data --dataset events --resume
```

If a downloaded events, lineup, or 360 file has no corresponding match object
in `matches/`, the default behavior is to stop and report the missing match.
To continue while recording each orphan file as skipped, explicitly use:

```powershell
uv run python manage.py ingest_dataset `
  --root data/data `
  --dataset events `
  --skip-missing-matches
```

Review the warnings and `ingestion_status` output before treating the run as
complete; skipped related-data files are not imported.

Force reprocessing is explicit and should be used only after inspecting the
impact:

```powershell
uv run python manage.py ingest_dataset --root data/data --dataset events --force
```

Inspect run checkpoints and validate imported relationships:

```powershell
uv run python manage.py ingestion_status
uv run python manage.py validate_ingestion
```

No production or unrestricted ingestion is performed by the test suite or by
this setup.
