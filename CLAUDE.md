# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendly — a Flask expense tracker built as a step-by-step student project. Routes in `app.py` are added incrementally; several are still placeholders (see below), and core logic (database, auth, expenses) is intentionally unimplemented until each "step" is completed.

## Commands

Run the app (from repo root, port 5001):
```
python app.py
```

Install dependencies:
```
pip install -r requirements.txt
```

Run tests (pytest + pytest-flask are declared as dependencies, but no test files exist yet in this repo — add them under a `tests/` directory as they're written):
```
pytest
pytest path/to/test_file.py::test_name   # single test
```

There is no build step, linter, or bundler configured — this is a server-rendered Flask app with plain CSS/JS, no frontend build tooling.

## Architecture

- **`app.py`** — single Flask entrypoint holding all routes. Routes fall into two groups:
  - Implemented: `/`, `/register`, `/login`, `/terms`, `/privacy` — render templates directly, no backend logic yet.
  - Placeholder (return plain strings, not yet wired to templates or the database): `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`. The comments above them ("Step 3", "Step 7", etc.) indicate the intended build order — implement in that sequence rather than jumping ahead.
- **`database/db.py`** — stub for the data layer. Intended to expose `get_db()` (SQLite connection, `row_factory` + foreign keys enabled), `init_db()` (idempotent `CREATE TABLE IF NOT EXISTS` schema), and `seed_db()` (sample dev data). None of this exists yet — this is the "Step 1" work referenced in `app.py`'s comments. `database/__init__.py` is empty.
- **`templates/`** — Jinja2 templates, all extending `templates/base.html` (nav, footer, font/CSS includes, `{% block content %}`). `register.html` and `login.html` already POST to `/register` and `/login` with `name`/`email`/`password` fields and render an `{% if error %}` block — the corresponding POST handlers in `app.py` don't exist yet and need to accept form data, validate, and hit the (not-yet-built) database layer.
- **`static/css/style.css`** — shared/global styles (nav, footer, auth forms). **`static/css/landing.css`** — landing-page-specific styles. **`static/js/main.js`** — currently empty; vanilla JS only, no framework/build step, per prior work on the landing page modal.
- SQLite is the target database (`expense_tracker.db`, gitignored) — no ORM is in use or expected; `database/db.py` uses raw `sqlite3`.

## Conventions

- No JS frameworks or added dependencies for frontend behavior — vanilla JS only (established when building the landing-page video modal).
- When editing a template for one specific feature, don't touch unrelated parts of that template or other pages.
