from datetime import datetime

from database.db import get_db


def _apply_date_range(where, params, start_date, end_date):
    if start_date:
        where += " AND date >= ?"
        params = params + [start_date]
    if end_date:
        where += " AND date <= ?"
        params = params + [end_date]
    return where, params


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created_at.strftime("%B %Y"),
    }


def get_summary_stats(user_id, start_date=None, end_date=None):
    conn = get_db()
    try:
        where, params = _apply_date_range("WHERE user_id = ?", [user_id], start_date, end_date)

        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            f"FROM expenses {where}",
            params,
        ).fetchone()
        top = conn.execute(
            f"SELECT category FROM expenses {where} "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            params,
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": round(totals["total"], 2),
        "transaction_count": totals["count"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    conn = get_db()
    try:
        where, params = _apply_date_range("WHERE user_id = ?", [user_id], start_date, end_date)
        params.append(limit)

        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            f"{where} ORDER BY date DESC, id DESC LIMIT ?",
            params,
        ).fetchall()
    finally:
        conn.close()

    transactions = []
    for row in rows:
        expense_date = datetime.strptime(row["date"], "%Y-%m-%d")
        transactions.append({
            "date": expense_date.strftime("%d %b %Y"),
            "description": row["description"],
            "category": row["category"],
            "amount": round(row["amount"], 2),
        })
    return transactions


def get_category_breakdown(user_id, start_date=None, end_date=None):
    conn = get_db()
    try:
        where, params = _apply_date_range("WHERE user_id = ?", [user_id], start_date, end_date)

        rows = conn.execute(
            "SELECT category, SUM(amount) AS amount FROM expenses "
            f"{where} GROUP BY category ORDER BY amount DESC",
            params,
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    total = sum(row["amount"] for row in rows)
    breakdown = [
        {"name": row["category"], "amount": round(row["amount"], 2), "pct": round(row["amount"] / total * 100)}
        for row in rows
    ]

    remainder = 100 - sum(item["pct"] for item in breakdown)
    breakdown[0]["pct"] += remainder

    return breakdown
