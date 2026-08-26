# Spec: Login and Logout

## Overview
Implements session-based sign-in and sign-out for Spendly. Users submit the
existing `login.html` form (email, password); the server verifies the
credentials against the `users` table, starts a Flask session, and redirects
to `/profile`. `/logout` clears that session and returns the user to the
landing page. This is the first place the app creates or destroys a Flask
session, so `app.secret_key` and session handling are introduced here. The
nav bar is also updated to reflect whether a visitor is signed in, since
that's the only user-visible proof that login/logout actually works at this
stage — `/profile` itself remains the Step 4 placeholder.

## Depends on
- Step 1 — Database setup. Requires `get_db()` and the `users` table
  (id, name, email, password_hash) to exist, which they do
  (`.claude/specs/01-database-setup.md`, complete).
- Step 2 — Registration. Requires at least one row in `users` with a
  werkzeug password hash to sign in against, which `POST /register`
  produces (`.claude/specs/02-registration.md`, complete).

## Routes
- `POST /login` — accept the existing form's `email`/`password` fields,
  look up the user by normalized email, verify the password hash, start a
  session, flash a "Welcome back, {name}!" message, redirect to `/` —
  public. (Extends the existing `GET /login` route rather than adding a
  new one.)
- `GET /logout` — clear the session and redirect to `/` — logged-in.
  (Replaces the existing placeholder that returns a plain string.)
- `GET|POST /login` and `GET|POST /register` — if a session is already
  active (`session.user_id` set), redirect to `/` immediately instead of
  showing the form, so a signed-in visitor can't land back on either auth
  page.

## Database changes
No database changes. `users` table already has every column this step needs.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — none needed; it already posts to `/login` and
    already renders `{% if error %}{{ error }}{% endif %}`
  - `templates/base.html`:
    - nav links become conditional on session state: signed out shows the
      existing "Sign in" / "Get started" links; signed in shows a "Profile"
      link and a "Logout" link (`{{ url_for('logout') }}`) instead
    - render `get_flashed_messages()` inside `<main>`, above
      `{% block content %}`, so the post-login welcome message (and any
      future flashed message) shows on whichever page it redirects to

## Files to change
- `app.py`:
  - Set `app.secret_key` (required for Flask `session`; not set anywhere
    yet — this is the first route to use sessions)
  - Import `session` and `flash` from `flask`
  - Change `/login` route to `methods=["GET", "POST"]`
  - At the top of both `/login` and `/register`: if `session.get("user_id")`
    is set, redirect to `url_for("landing")` immediately (before checking
    `request.method`) — an already-signed-in visitor never sees either form
  - On POST: normalize email (`strip().lower()`), fetch the matching user
    via `get_db()`, verify the password with `check_password_hash`, set
    `session["user_id"] = user["id"]`, `flash(f"Welcome back, {user['name']}!")`,
    redirect to `url_for("landing")`
  - On missing fields or invalid credentials: re-render `login.html` with a
    generic `error` message (e.g. "Invalid email or password.") — do not
    reveal whether the email exists
  - Replace the `/logout` placeholder body: `session.clear()`, redirect to
    `url_for("landing")`
- `templates/base.html`:
  - Wrap the existing nav links in `{% if session.user_id %}` / `{% else %}`
    so signed-in visitors see "Profile" / "Logout" instead of
    "Sign in" / "Get started"

## Files to create
None

## New dependencies
No new dependencies — `session` and `check_password_hash` are part of
Flask/werkzeug core, already installed.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (verify with `check_password_hash`, never
  compare hashes or plaintext directly)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Re-render `login.html` with `error` on failure rather than redirecting to
  a separate error page
- Use one generic error message for both "no such email" and "wrong
  password" so login never leaks which emails are registered
- Normalize email (strip + lowercase) before the lookup, matching how
  `/register` stores it

## Definition of done
- [ ] Submitting the login form with a valid, registered email and correct
      password redirects to `/` with a "Welcome back, {name}!" message and
      sets a session cookie
- [ ] Submitting with a correct email but wrong password re-renders
      `login.html` with a generic error and does not set a session
- [ ] Submitting with an email that isn't registered re-renders
      `login.html` with the same generic error
- [ ] Submitting with a missing field re-renders `login.html` with an error
- [ ] Visiting `/logout` while signed in clears the session and redirects
      to `/`
- [ ] After `/logout`, the nav bar shows "Sign in" / "Get started" again
- [ ] While signed in, the nav bar shows "Profile" / "Logout" instead of
      "Sign in" / "Get started"
- [ ] While signed in, visiting `/login` or `/register` redirects to `/`
      instead of showing the form
- [ ] `GET /login` still renders the empty form exactly as before when
      signed out
- [ ] App starts and runs without errors after the change
