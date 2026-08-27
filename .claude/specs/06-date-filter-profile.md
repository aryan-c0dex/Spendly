# Spec: Date Filter for Profile Page

## Overview
Step 6 adds date-range filtering to the `/profile` page. Currently the profile
route always shows all-time summary stats, the 10 most recent transactions,
and an all-time category breakdown. This step lets a logged-in user narrow
those three sections to a specific date range — either a quick preset (This
Month, Last Month, Last 3 Months, This Year, All Time) or a custom start/end
date — so they can answer "how much did I spend in March?" without leaving
the page.

## Depends on
- Step 1: Database setup (`expenses.date` column, `get_db()`)
- Step 3: Login / Logout (`session["user_id"]` required to view the page)
- Step 5: Backend routes for profile page (`database/queries.py` helpers and
  the live-data `/profile` route this step modifies)

## Routes
No new routes. `GET /profile` is modified to accept two optional query
string parameters:
- `start` — ISO date (`YYYY-MM-DD`), inclusive lower bound
- `end` — ISO date (`YYYY-MM-DD`), inclusive upper bound

Both are optional and independent (only `start`, only `end`, both, or
neither — neither means all-time, matching current behaviour). Access level:
logged-in only, same as today.

## Database changes
No database changes. `expenses.date` is already stored as an ISO
`YYYY-MM-DD` string, which sorts and compares correctly with plain SQL
`>=` / `<=` operators — no schema change needed.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter bar above the stats row: a plain `<form method="get">` with
    two `<input type="date">` fields (`start`, `end`) and a submit button,
    plus preset links (This Month / Last Month / Last 3 Months / This Year /
    All Time) that link to `/profile` with the appropriate `start`/`end`
    query params already computed server-side.
  - Show the active filter's human-readable label (e.g. "Showing: 1 Mar 2026
    – 31 Mar 2026") when a filter is applied, with a "Clear filter" link back
    to plain `/profile`.
  - No structural change to the stats row, transaction table, or breakdown
    card — they keep consuming the same variable names, just filtered data.

## Files to change
- `app.py` — `profile()` reads `start`/`end` from `request.args`, validates
  they parse as ISO dates (ignore/discard silently if not), computes the five
  preset ranges and their query strings, and passes `start`, `end`, `presets`,
  and a computed `filter_label` into the template.
- `database/queries.py` — add optional `start_date=None, end_date=None`
  keyword args to `get_summary_stats`, `get_recent_transactions`, and
  `get_category_breakdown`; when provided, append parameterised
  `AND date >= ?` / `AND date <= ?` clauses to the existing queries.
- `templates/profile.html` — add the filter bar described above.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format `start`/`end` into SQL
- Passwords hashed with werkzeug (unaffected by this step, but preserve
  existing auth code as-is)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency stays ₹ everywhere, consistent with Step 5
- An invalid or malformed `start`/`end` value must never raise a 500 — treat
  it as if that bound were absent
- If `start` is after `end`, treat the filter as producing zero results
  rather than erroring
- Preset ranges are computed in `app.py` using the server's current date
  (`date.today()`), not in JavaScript — no JS framework or added dependency
  for this feature
- Query helpers keep opening/closing their own connection via `get_db()`,
  same pattern as Step 5

## Definition of done
- [ ] Visiting `/profile` with no query params behaves exactly as before
      (all-time stats, 8 transactions for the seed user, full breakdown)
- [ ] Clicking "This Month" filters the stats, transaction list, and
      breakdown to only expenses dated in the current calendar month
- [ ] Clicking "Last Month", "Last 3 Months", and "This Year" each produce
      the correct filtered results for the seed data
- [ ] Manually entering a custom `start` and `end` date in the form and
      submitting filters correctly to that inclusive range
- [ ] A `start` date after the `end` date shows zero transactions, ₹0.00
      total, and an empty breakdown — no error page
- [ ] An invalid date string in the query string (e.g. `?start=notadate`) is
      ignored and the page still renders (falls back to no lower bound)
- [ ] "Clear filter" returns to `/profile` with no query params and restores
      all-time data
- [ ] All amounts on the filtered page still display the ₹ symbol
