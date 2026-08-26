# Spec: Registration

## Overview
Implements account creation for Spendly. Users submit the existing
`register.html` form (name, email, password); the server validates input,
hashes the password with werkzeug, inserts a new row into `users`, starts a
session for the new user, and redirects them to `/profile`. This is the
first piece of real backend logic in the app and the foundation every later
authenticated step (profile, expenses) builds on.

## Depends on
- Step 1 — Database setup. Requires `get_db()`, `init_db()`, and the
  `users` table (id, name, email, password_hash, created_at) to already
  exist, which they do (`.claude/specs/01-database-setup.md`, complete).

## Routes
- `POST /register` — accept the existing form's `name`/`email`/`password`
  fields, validate, hash password, insert user, start session, redirect to
  `/profile` — public. (Extends the existing `GET /register` route rather
  than adding a new one.)

## Database changes
No database changes. `users` table already has every column this step
needs.

## Templates
- **Create:** none
- **Modify:** none — `register.html` already posts to `/register` and
  already renders `{% if error %}{{ error }}{% endif %}`

## Files to change
- `app.py`:
  - Set `app.secret_key` (required for Flask `session`)
  - Import `request`, `redirect`, `url_for`, `session` from `flask`
  - Change `/register` route to `methods=["GET", "POST"]`
  - On POST: validate required fields, validate password length >= 8,
    normalize email (`strip().lower()`), check for existing email via
    `get_db()`, hash password with `generate_password_hash`, insert user,
    `session["user_id"] = user_id`, `redirect(url_for("profile"))`
  - On validation/duplicate-email failure: re-render `register.html` with
    an `error` message (no redirect)

## Files to create
None

## New dependencies
No new dependencies — `session` is part of Flask core, already installed.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Re-render `register.html` with `error` on failure rather than redirecting
  to a separate error page
- Normalize email (strip + lowercase) before the uniqueness check and the
  insert
- Enforce a minimum password length of 8 characters server-side (matches
  the form's placeholder hint)

## Definition of done
- [ ] Submitting the register form with valid, unique details creates a new
      row in `users` with a hashed password
- [ ] Submitting with an email that already exists re-renders
      `register.html` with an error and does not insert a duplicate row
- [ ] Submitting with a missing field re-renders `register.html` with an
      error and does not insert a row
- [ ] Submitting with a password under 8 characters re-renders
      `register.html` with an error
- [ ] On success, the browser is redirected to `/profile` and a session
      cookie is set
- [ ] `GET /register` still renders the empty form exactly as before
- [ ] App starts and runs without errors after the change
