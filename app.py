from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")

        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters.")

        conn = get_db()
        try:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                return render_template("register.html", error="An account with that email already exists.")

            password_hash = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
            conn.commit()
        finally:
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Invalid email or password.")

        conn = get_db()
        try:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        finally:
            conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")

        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}!")
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
    finally:
        conn.close()

    name = row["name"]
    initials = "".join(part[0] for part in name.split()[:2]).upper()
    created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")

    user = {
        "name": name,
        "email": row["email"],
        "initials": initials,
        "member_since": created_at.strftime("%B %Y"),
    }
    stats = {
        "total_spent": 18240,
        "transaction_count": 34,
        "top_category": "Food",
    }
    transactions = [
        {"date": "22 Aug 2026", "description": "Restaurant dinner", "category": "Food", "amount": 850},
        {"date": "18 Aug 2026", "description": "New shoes", "category": "Shopping", "amount": 3200},
        {"date": "14 Aug 2026", "description": "Movie night", "category": "Entertainment", "amount": 600},
        {"date": "10 Aug 2026", "description": "Electricity bill", "category": "Bills", "amount": 1899},
        {"date": "05 Aug 2026", "description": "Bus pass top-up", "category": "Transport", "amount": 400},
    ]
    breakdown = [
        {"category": "Food", "amount": 6200, "percent": 78},
        {"category": "Shopping", "amount": 4400, "percent": 55},
        {"category": "Bills", "amount": 3399, "percent": 42},
        {"category": "Transport", "amount": 2100, "percent": 26},
    ]

    return render_template(
        "profile.html",
        user=user, stats=stats,
        transactions=transactions, breakdown=breakdown,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
