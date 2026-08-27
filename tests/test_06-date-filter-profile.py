"""
Tests for Step 6 — Date Filter for Profile Page.

Spec: .claude/specs/06-date-filter-profile.md

`GET /profile` gains two optional, independent query-string params, `start`
and `end` (inclusive ISO YYYY-MM-DD bounds). These tests exercise the
contract described in the spec's "Definition of done" section:

- No params  -> identical, all-time behaviour (unchanged baseline)
- Preset links (This Month / Last Month / Last 3 Months / This Year /
  All Time) filter stats, transactions, and breakdown correctly
- A manually-entered custom start/end filters an inclusive range
- start > end yields zero results, not an error
- An invalid/malformed date string is silently ignored (treated as absent),
  never a 500
- "Clear filter" returns to plain /profile with full data restored
- The rupee (₹) symbol is always present, filtered or not
- The route stays login-gated

None of these assertions are derived from reading app.py's/queries.py's
internals — only route paths, session keys, and template markup (needed to
locate values in rendered HTML) were read for structural facts.
"""
import html as html_lib
import re
from datetime import date

import pytest
from flask import url_for

from conftest import (
    count_expenses,
    get_user_id_by_email,
    insert_expense,
    register_and_login,
)

# --------------------------------------------------------------------- #
# Known facts about the seeded demo user (database/db.py `_sample_expenses`)
# 8 expenses, all dated within the *current* calendar month at import time.
# --------------------------------------------------------------------- #
SEED_TOTAL = 436.24
SEED_COUNT = 8
SEED_TOP_CATEGORY = "Shopping"
SEED_CATEGORY_COUNT = 7  # Food, Transport, Bills, Health, Entertainment, Shopping, Other

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"


# --------------------------------------------------------------------- #
# Small HTML-scraping helpers (based on templates/profile.html markup)   #
# --------------------------------------------------------------------- #

def _login_demo(client):
    resp = client.post(
        "/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, follow_redirects=False
    )
    assert resp.status_code == 302, "expected demo login to succeed"


def _extract_stat_value(text, label):
    pattern = rf'{re.escape(label)}</span>\s*<span class="stat-value">([^<]+)</span>'
    match = re.search(pattern, text)
    assert match, f"could not find stat card for {label!r} in response"
    return match.group(1).strip()


def _get_total_spent(text):
    raw = _extract_stat_value(text, "Total spent").replace("₹", "").replace(",", "")
    return float(raw)


def _get_transaction_count(text):
    return int(_extract_stat_value(text, "Transactions"))


def _count_transaction_rows(text):
    match = re.search(r"<tbody>(.*?)</tbody>", text, re.S)
    assert match, "transaction table <tbody> not found in response"
    return match.group(1).count("<tr>")


def _count_breakdown_rows(text):
    return text.count('class="breakdown-row"')


def _extract_preset_href(text, label):
    pattern = rf'<a href="([^"]+)" class="btn-ghost">{re.escape(label)}</a>'
    match = re.search(pattern, text)
    assert match, f"could not find preset link for {label!r} in response"
    return html_lib.unescape(match.group(1))


def _shift_month(year, month, delta):
    total = (year * 12 + (month - 1)) + delta
    return total // 12, total % 12 + 1


# --------------------------------------------------------------------- #
# Fixture: a fresh (non-seeded) user with controlled, known expense dates #
# used for tests that need precise date-boundary control.                #
# --------------------------------------------------------------------- #

@pytest.fixture
def custom_client(client):
    """Fresh user with 4 expenses spanning Jan 2024 -> Feb 2024, known amounts."""
    email = register_and_login(client, name="Custom Range Tester", email="custom@test.com")
    user_id = get_user_id_by_email(email)

    insert_expense(user_id, 10.00, "Food", "2024-01-01", "JanFirst")
    insert_expense(user_id, 20.00, "Transport", "2024-01-15", "JanMid")
    insert_expense(user_id, 30.00, "Bills", "2024-01-31", "JanLast")
    insert_expense(user_id, 40.00, "Health", "2024-02-01", "FebFirst")

    return client


@pytest.fixture
def calendar_client(client):
    """Fresh user with one expense per relevant calendar bucket, anchored to
    today's real date so 'This Month' / 'Last Month' / 'This Year' presets
    can be exercised without hardcoding the app's own boundary math."""
    email = register_and_login(client, name="Calendar Tester", email="calendar@test.com")
    user_id = get_user_id_by_email(email)

    today = date.today()
    this_month_first = today.replace(day=1)
    ly, lm = _shift_month(today.year, today.month, -1)
    last_month_first = date(ly, lm, 1)
    prior_year_date = date(today.year - 1, 1, 1)

    insert_expense(user_id, 111.11, "Food", this_month_first.isoformat(), "ThisMonthExpense")
    insert_expense(user_id, 222.22, "Transport", last_month_first.isoformat(), "LastMonthExpense")
    insert_expense(user_id, 333.33, "Bills", prior_year_date.isoformat(), "PriorYearExpense")

    return client


# ======================================================================= #
# Auth guard                                                              #
# ======================================================================= #

class TestAuthGuard:
    def test_profile_without_login_redirects_to_login(self, client, app):
        with app.test_request_context():
            login_url = url_for("login")
        resp = client.get("/profile", follow_redirects=False)
        assert resp.status_code == 302, "unauthenticated /profile should redirect"
        assert resp.headers["Location"].endswith(login_url), "should redirect to /login"

    def test_profile_with_filter_params_without_login_still_redirects(self, client):
        resp = client.get("/profile?start=2024-01-01&end=2024-01-31", follow_redirects=False)
        assert resp.status_code == 302, "auth guard must apply even with query params present"


# ======================================================================= #
# DoD: no query params behaves exactly as before (baseline / all-time)    #
# ======================================================================= #

class TestNoFilterBaseline:
    def test_no_params_returns_all_time_seed_data(self, client):
        _login_demo(client)
        resp = client.get("/profile")
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200
        assert _get_transaction_count(text) == SEED_COUNT, "expected all 8 seed transactions"
        assert _count_transaction_rows(text) == SEED_COUNT
        assert _get_total_spent(text) == pytest.approx(SEED_TOTAL, abs=0.01)
        assert SEED_TOP_CATEGORY in text
        assert _count_breakdown_rows(text) == SEED_CATEGORY_COUNT

    def test_no_params_shows_no_active_filter_label_or_clear_link(self, client):
        _login_demo(client)
        resp = client.get("/profile")
        text = resp.get_data(as_text=True)

        assert "Showing:" not in text, "no filter should mean no 'Showing:' label"
        assert "Clear filter" not in text, "no filter should mean no clear-filter link"

    def test_no_params_presets_are_all_present(self, client):
        _login_demo(client)
        resp = client.get("/profile")
        text = resp.get_data(as_text=True)

        for label in ("This Month", "Last Month", "Last 3 Months", "This Year", "All Time"):
            assert label in text, f"expected preset link {label!r} on profile page"


# ======================================================================= #
# DoD: preset links filter correctly                                      #
# ======================================================================= #

class TestPresetFilters:
    def test_this_month_preset_includes_current_month_excludes_others(self, client, calendar_client):
        resp = client.get("/profile")
        text = resp.get_data(as_text=True)
        href = _extract_preset_href(text, "This Month")

        filtered = client.get(href)
        ftext = filtered.get_data(as_text=True)

        assert filtered.status_code == 200
        assert "ThisMonthExpense" in ftext
        assert "LastMonthExpense" not in ftext
        assert "PriorYearExpense" not in ftext

    def test_last_month_preset_includes_last_month_excludes_current(self, client, calendar_client):
        resp = client.get("/profile")
        text = resp.get_data(as_text=True)
        href = _extract_preset_href(text, "Last Month")

        filtered = client.get(href)
        ftext = filtered.get_data(as_text=True)

        assert filtered.status_code == 200
        assert "LastMonthExpense" in ftext
        assert "ThisMonthExpense" not in ftext
        assert "PriorYearExpense" not in ftext

    def test_last_3_months_preset_includes_this_and_last_month(self, client, calendar_client):
        resp = client.get("/profile")
        text = resp.get_data(as_text=True)
        href = _extract_preset_href(text, "Last 3 Months")

        filtered = client.get(href)
        ftext = filtered.get_data(as_text=True)

        assert filtered.status_code == 200
        assert "ThisMonthExpense" in ftext
        assert "LastMonthExpense" in ftext
        assert "PriorYearExpense" not in ftext

    def test_this_year_preset_includes_this_year_excludes_prior_year(self, client, calendar_client):
        resp = client.get("/profile")
        text = resp.get_data(as_text=True)
        href = _extract_preset_href(text, "This Year")

        filtered = client.get(href)
        ftext = filtered.get_data(as_text=True)

        assert filtered.status_code == 200
        assert "ThisMonthExpense" in ftext
        assert "PriorYearExpense" not in ftext

    def test_all_time_preset_restores_full_seed_data(self, client):
        _login_demo(client)
        filtered = client.get("/profile?start=2024-01-01&end=2024-01-31")
        ftext = filtered.get_data(as_text=True)
        href = _extract_preset_href(ftext, "All Time")

        restored = client.get(href)
        rtext = restored.get_data(as_text=True)

        assert restored.status_code == 200
        assert _get_transaction_count(rtext) == SEED_COUNT
        assert _get_total_spent(rtext) == pytest.approx(SEED_TOTAL, abs=0.01)


# ======================================================================= #
# DoD: manual custom start/end filters an inclusive range                 #
# ======================================================================= #

class TestCustomRangeFilter:
    def test_full_range_includes_inclusive_bounds_excludes_outside(self, custom_client):
        resp = custom_client.get("/profile?start=2024-01-01&end=2024-01-31")
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200
        assert "JanFirst" in text, "start date itself must be included (inclusive lower bound)"
        assert "JanMid" in text
        assert "JanLast" in text, "end date itself must be included (inclusive upper bound)"
        assert "FebFirst" not in text, "date after end must be excluded"
        assert _get_transaction_count(text) == 3
        assert _get_total_spent(text) == pytest.approx(60.00, abs=0.01)

    def test_start_only_filters_from_start_onward(self, custom_client):
        resp = custom_client.get("/profile?start=2024-01-15")
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200
        assert "JanFirst" not in text
        assert "JanMid" in text
        assert "JanLast" in text
        assert "FebFirst" in text
        assert _get_transaction_count(text) == 3

    def test_end_only_filters_up_to_end(self, custom_client):
        resp = custom_client.get("/profile?end=2024-01-15")
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200
        assert "JanFirst" in text
        assert "JanMid" in text
        assert "JanLast" not in text
        assert "FebFirst" not in text
        assert _get_transaction_count(text) == 2

    def test_form_inputs_echo_submitted_start_and_end(self, custom_client):
        resp = custom_client.get("/profile?start=2024-01-01&end=2024-01-31")
        text = resp.get_data(as_text=True)

        assert 'id="start"' in text and 'value="2024-01-01"' in text
        assert 'id="end"' in text and 'value="2024-01-31"' in text

    def test_filter_label_reflects_active_range(self, custom_client):
        resp = custom_client.get("/profile?start=2024-01-01&end=2024-01-31")
        text = resp.get_data(as_text=True)

        assert "Showing:" in text
        assert "Clear filter" in text


# ======================================================================= #
# DoD: start after end -> zero results, not an error                      #
# ======================================================================= #

class TestStartAfterEnd:
    def test_start_after_end_yields_zero_results_no_error(self, custom_client):
        resp = custom_client.get("/profile?start=2024-02-01&end=2024-01-01")
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200, "start > end must never produce an error page"
        assert _get_transaction_count(text) == 0
        assert _get_total_spent(text) == pytest.approx(0.0, abs=0.01)
        assert _count_transaction_rows(text) == 0
        assert _count_breakdown_rows(text) == 0, "breakdown must be empty, not erroring"
        for desc in ("JanFirst", "JanMid", "JanLast", "FebFirst"):
            assert desc not in text

    def test_start_after_end_still_shows_rupee_symbol(self, custom_client):
        resp = custom_client.get("/profile?start=2024-02-01&end=2024-01-01")
        text = resp.get_data(as_text=True)
        assert "₹" in text, "amounts (even zero) must still show the ₹ symbol"
        assert re.search(r"₹\s*0(\.0+)?\b", text), "zero total should render as a ₹0 amount"


# ======================================================================= #
# DoD: invalid/malformed date strings are silently ignored, never a 500   #
# ======================================================================= #

class TestInvalidDateHandling:
    def test_invalid_start_is_ignored_falls_back_to_no_lower_bound(self, custom_client):
        resp = custom_client.get("/profile?start=notadate")
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200, "invalid start must never raise a 500"
        # No valid lower bound and no upper bound supplied -> behaves as all-time
        assert _get_transaction_count(text) == 4
        for desc in ("JanFirst", "JanMid", "JanLast", "FebFirst"):
            assert desc in text

    def test_invalid_end_is_ignored_falls_back_to_no_upper_bound(self, custom_client):
        resp = custom_client.get("/profile?end=31-01-2024")  # wrong format, not ISO
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200, "invalid end must never raise a 500"
        assert _get_transaction_count(text) == 4

    def test_both_invalid_behaves_as_all_time(self, custom_client):
        resp = custom_client.get("/profile?start=xxxx&end=yyyy")
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200
        assert _get_transaction_count(text) == 4

    def test_empty_string_params_treated_as_absent(self, custom_client):
        resp = custom_client.get("/profile?start=&end=")
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200
        assert _get_transaction_count(text) == 4

    @pytest.mark.parametrize(
        "bad_value",
        [
            "2024-13-40",         # out-of-range month/day
            "not-a-date-at-all",
            "2024/01/01",          # wrong separator
            "' OR '1'='1",         # SQL injection attempt
            "1; DROP TABLE expenses;--",
            "x" * 500,              # very long input
        ],
    )
    def test_malformed_start_values_never_500_and_db_stays_intact(self, custom_client, bad_value):
        before = count_expenses()
        resp = custom_client.get("/profile", query_string={"start": bad_value})

        assert resp.status_code == 200, f"malformed start={bad_value!r} must not raise a 500"
        assert count_expenses() == before, "malformed input must not mutate the database"


# ======================================================================= #
# DoD: "Clear filter" returns to plain /profile, restores all-time data   #
# ======================================================================= #

class TestClearFilter:
    def test_clear_filter_link_present_only_when_filtered(self, custom_client):
        filtered = custom_client.get("/profile?start=2024-01-01&end=2024-01-31")
        assert "Clear filter" in filtered.get_data(as_text=True)

        unfiltered = custom_client.get("/profile")
        assert "Clear filter" not in unfiltered.get_data(as_text=True)

    def test_clicking_clear_filter_restores_all_time_data(self, custom_client, app):
        filtered = custom_client.get("/profile?start=2024-01-01&end=2024-01-31")
        text = filtered.get_data(as_text=True)

        match = re.search(r'<a href="([^"]+)">Clear filter</a>', text)
        assert match, "expected a 'Clear filter' link back to /profile"
        clear_href = html_lib.unescape(match.group(1))

        with app.test_request_context():
            assert clear_href == url_for("profile"), "clear filter must link to plain /profile"

        restored = custom_client.get(clear_href)
        rtext = restored.get_data(as_text=True)

        assert restored.status_code == 200
        assert _get_transaction_count(rtext) == 4
        for desc in ("JanFirst", "JanMid", "JanLast", "FebFirst"):
            assert desc in rtext


# ======================================================================= #
# DoD: ₹ symbol always present on the filtered page                       #
# ======================================================================= #

class TestCurrencySymbol:
    @pytest.mark.parametrize(
        "query_string",
        [
            "",
            "?start=2024-01-01&end=2024-01-31",
            "?start=2024-02-01&end=2024-01-01",  # zero-result case
            "?start=notadate",
        ],
    )
    def test_rupee_symbol_present_regardless_of_filter_state(self, custom_client, query_string):
        resp = custom_client.get(f"/profile{query_string}")
        text = resp.get_data(as_text=True)

        assert resp.status_code == 200
        assert "₹" in text, "₹ must be shown for every filter state"
