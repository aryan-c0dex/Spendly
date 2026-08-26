import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "expense_tracker.db")

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        if existing["c"] > 0:
            return

        password_hash = generate_password_hash("demo123")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cur.lastrowid

        for amount, category, day, description in _sample_expenses():
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, _date_in_current_month(day), description),
            )
        conn.commit()
    finally:
        conn.close()


def _date_in_current_month(day):
    today = date.today()
    return today.replace(day=min(day, 28)).isoformat()


def _sample_expenses():
    # (amount, category, day-of-month, description) — 8 rows, all 7 categories covered
    return [
        (45.50, "Food", 3, "Grocery shopping"),
        (12.00, "Transport", 5, "Bus pass top-up"),
        (89.99, "Bills", 1, "Electricity bill"),
        (25.00, "Health", 8, "Pharmacy"),
        (60.00, "Entertainment", 10, "Movie night"),
        (150.00, "Shopping", 14, "New shoes"),
        (20.00, "Other", 18, "Miscellaneous"),
        (33.75, "Food", 22, "Restaurant dinner"),
    ]
