from datetime import date, datetime, timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

app = Flask(__name__)
app.secret_key = "dev"


# ------------------------------------------------------------------ #
# Date filter helpers                                                 #
# ------------------------------------------------------------------ #

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _add_months(year, month, delta):
    total = (year * 12 + (month - 1)) + delta
    return total // 12, total % 12 + 1


def _month_bounds(year, month):
    start = date(year, month, 1)
    ny, nm = _add_months(year, month, 1)
    end = date(ny, nm, 1) - timedelta(days=1)
    return start, end


def _preset_url(start=None, end=None):
    kwargs = {}
    if start:
        kwargs["start"] = start.isoformat()
    if end:
        kwargs["end"] = end.isoformat()
    return url_for("profile", **kwargs)


def _build_presets():
    today = date.today()
    this_start, this_end = _month_bounds(today.year, today.month)
    last_y, last_m = _add_months(today.year, today.month, -1)
    last_start, last_end = _month_bounds(last_y, last_m)
    l3_y, l3_m = _add_months(today.year, today.month, -2)
    l3_start, _ = _month_bounds(l3_y, l3_m)
    year_start, year_end = date(today.year, 1, 1), date(today.year, 12, 31)

    return [
        {"label": "This Month", "url": _preset_url(this_start, this_end)},
        {"label": "Last Month", "url": _preset_url(last_start, last_end)},
        {"label": "Last 3 Months", "url": _preset_url(l3_start, this_end)},
        {"label": "This Year", "url": _preset_url(year_start, year_end)},
        {"label": "All Time", "url": _preset_url()},
    ]


def _format_label_date(value):
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return f"{parsed.day} {parsed:%b %Y}"


def _build_filter_label(start, end):
    if start and end:
        return f"Showing: {_format_label_date(start)} – {_format_label_date(end)}"
    if start:
        return f"Showing: from {_format_label_date(start)}"
    if end:
        return f"Showing: through {_format_label_date(end)}"
    return None


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

    user_id = session["user_id"]
    user_row = get_user_by_id(user_id)
    name = user_row["name"]
    initials = "".join(part[0] for part in name.split()[:2]).upper()

    user = {
        "name": name,
        "email": user_row["email"],
        "initials": initials,
        "member_since": user_row["member_since"],
    }
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))

    stats = get_summary_stats(user_id, start_date=start, end_date=end)
    transactions = get_recent_transactions(user_id, start_date=start, end_date=end)
    breakdown = [
        {"category": row["name"], "amount": row["amount"], "percent": row["pct"]}
        for row in get_category_breakdown(user_id, start_date=start, end_date=end)
    ]

    return render_template(
        "profile.html",
        user=user, stats=stats,
        transactions=transactions, breakdown=breakdown,
        start=start, end=end,
        filter_label=_build_filter_label(start, end),
        presets=_build_presets(),
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
