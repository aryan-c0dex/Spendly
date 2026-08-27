"""
Shared pytest fixtures for the Spendly test suite.

Because `database/db.py` opens a brand-new sqlite3 connection per call using
a module-level `DB_PATH` constant (there is no Flask `app.config['DATABASE']`
indirection in this codebase), test isolation is achieved by monkeypatching
`database.db.DB_PATH` to a throwaway temp-file database before each test and
re-running `init_db()` / `seed_db()` against it. This keeps tests from ever
touching the real `expense_tracker.db` used by `python app.py`.
"""
import os
import sys
import tempfile

# Make sure the repo root (which holds app.py and the database/ package) is
# importable regardless of how/where pytest is invoked from.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import database.db as db_module  # noqa: E402

# app.py runs `init_db()` / `seed_db()` at *import* time (module-level code).
# Redirect DB_PATH to a scratch file *before* importing app, so that
# first-import side effect never writes to the real project database.
_import_time_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_import_time_db.close()
db_module.DB_PATH = _import_time_db.name

import app as app_module  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture
def app(monkeypatch, tmp_path):
    """A Flask app wired to a fresh, isolated, seeded sqlite DB per test."""
    db_file = tmp_path / "spendly_test.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_file))

    flask_app = app_module.app
    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
        }
    )

    db_module.init_db()
    db_module.seed_db()

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# --------------------------------------------------------------------- #
# Helpers (not fixtures) for building test data directly against the DB #
# --------------------------------------------------------------------- #

def register_and_login(client, name="Filter Tester", email="filter@test.com", password="testpass123"):
    """Register a brand-new user and log them in via the real routes."""
    client.post("/register", data={"name": name, "email": email, "password": password})
    resp = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert resp.status_code == 302, "expected login to succeed and redirect"
    return email


def get_user_id_by_email(email):
    conn = db_module.get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()
    assert row is not None, f"no user found for {email!r}"
    return row["id"]


def insert_expense(user_id, amount, category, date_str, description):
    conn = db_module.get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date_str, description),
        )
        conn.commit()
    finally:
        conn.close()


def count_expenses():
    conn = db_module.get_db()
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()
    finally:
        conn.close()
    return row["c"]
