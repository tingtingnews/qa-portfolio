"""
test_analytics_performance.py
UI + API tests for Shping Admin — Analytics > Performance tab
(URL: /admin/analytics/overview)

Participant: Authenticateit Pty Ltd

Classes:
  1. TestPerformanceCharts    — UI widget / KPI rendering
  2. TestPerformanceFilters   — date range, dropdowns, radio toggle
  3. TestPerformanceAPI       — BE request & response validation
  4. TestPerformanceBEvsUI    — FE/BE data consistency
  5. TestPerformanceAggregation — daily vs weekly/monthly sums
  6. TestPerformanceDateChange  — different ranges → different data

Run:
    pytest test_analytics_performance.py -v --headed
"""

import re
import json
import datetime
import pytest
from playwright.sync_api import Page, expect

from conftest import (
    ANALYTICS_PERF_URL,
    API_BASE_URL,
    BASE_URL,
)

GRAPHQL_URL = f"{API_BASE_URL}/graphql"

# Date ranges — FULL_RANGE is dynamic: Jan 1 of the current year → today
_today     = datetime.date.today()
_start     = datetime.date(_today.year, 1, 1)
FULL_RANGE = (_start.strftime("%m/%d/%Y"), _today.strftime("%m/%d/%Y"))
RANGE_A    = ("01/01/2026", "01/31/2026")   # January
RANGE_B    = ("03/01/2026", "03/31/2026")   # March


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def set_date_range(page: Page, start: str, end: str) -> None:
    inputs = page.locator("input")
    date_inputs = [
        inputs.nth(i)
        for i in range(inputs.count())
        if re.match(r"\d{2}/\d{2}/\d{4}", inputs.nth(i).input_value())
    ]
    if len(date_inputs) < 2:
        pytest.skip("Date picker inputs not found")

    date_inputs[0].click(click_count=3)
    date_inputs[0].type(start)
    page.keyboard.press("Tab")

    date_inputs[1].click(click_count=3)
    date_inputs[1].type(end)
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")

    page.evaluate("window.scrollBy(0, 600)")
    page.wait_for_timeout(500)
    page.evaluate("window.scrollBy(0, 600)")
    page.wait_for_timeout(500)

    try:
        page.wait_for_load_state("networkidle", timeout=12_000)
    except Exception:
        pass
    page.wait_for_timeout(3000)


def capture_requests(page: Page, action_fn) -> list[dict]:
    payloads: list[dict] = []

    def handler(req):
        if req.url == GRAPHQL_URL and req.method == "POST":
            try:
                payloads.append(json.loads(req.post_data or "{}"))
            except Exception:
                pass

    page.on("request", handler)
    try:
        action_fn()
    finally:
        page.remove_listener("request", handler)
    return payloads


def capture_responses(page: Page, action_fn) -> list[dict]:
    bodies: list[dict] = []

    def handler(resp):
        if resp.url == GRAPHQL_URL and resp.status == 200:
            try:
                bodies.append(resp.json())
            except Exception:
                pass

    page.on("response", handler)
    try:
        action_fn()
    finally:
        page.remove_listener("response", handler)
    return bodies


def get_daily_engagement(bodies: list[dict]) -> list[dict]:
    # Return the LONGEST engagement list across all captured responses.
    # When fresh_load() runs inside a capture window, both the initial page-load
    # response (default/stale date range) and the FULL_RANGE response are captured.
    # Taking the longest list ensures the real data wins over any short stale response.
    candidates = [
        b.get("data", {}).get("analytics", {}).get("engagements", [])
        for b in bodies
    ]
    candidates = [c for c in candidates if c and "day" in c[0]]
    return max(candidates, key=len) if candidates else []


def get_top_products(bodies: list[dict]) -> list[dict]:
    candidates = [
        b.get("data", {}).get("analytics", {}).get("top_products", [])
        for b in bodies
    ]
    candidates = [c for c in candidates if c]
    return max(candidates, key=len) if candidates else []


def get_top_users(bodies: list[dict]) -> list[dict]:
    candidates = [
        b.get("data", {}).get("analytics", {}).get("top_users", [])
        for b in bodies
    ]
    candidates = [c for c in candidates if c]
    return max(candidates, key=len) if candidates else []


def _flush(page: Page) -> None:
    """Wait for in-flight requests to settle between back-to-back captures."""
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass
    page.wait_for_timeout(3_000)


def parse_mmddyyyy(date_str: str) -> datetime.date:
    m, d, y = date_str.split("/")
    return datetime.date(int(y), int(m), int(d))


def fresh_load(page: Page, start: str, end: str) -> None:
    page.goto(ANALYTICS_PERF_URL)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass
    page.wait_for_selector("h3:has-text('Reach')", timeout=30_000)
    set_date_range(page, start, end)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. UI CHART / WIDGET TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceCharts:

    def test_kpi_widgets_visible(self, analytics_page: Page):
        for name in ["Reach", "Interactions", "Spend", "Sales projection"]:
            expect(analytics_page.get_by_role("heading", name=name)).to_be_visible()

    def test_kpi_values_valid(self, analytics_page: Page):
        reach_widget = analytics_page.get_by_role("heading", name="Reach").locator("..").locator("..")
        assert re.search(r"\d", reach_widget.inner_text()), "Reach has no number"

        spend_widget = analytics_page.get_by_role("heading", name="Spend").locator("..").locator("..")
        assert "$" in spend_widget.inner_text(), "Spend missing '$'"

        proj_widget = analytics_page.get_by_role("heading", name="Sales projection").locator("..").locator("..")
        proj_text = proj_widget.inner_text()
        assert "$" in proj_text, f"Sales projection missing '$': '{proj_text}'"
        assert "items" in proj_text.lower(), f"Sales projection missing 'items': '{proj_text}'"

    def test_daily_engagement_chart(self, analytics_page: Page):
        expect(analytics_page.get_by_text("Daily Engagement", exact=True)).to_be_visible()

    def test_top_products_table(self, analytics_page: Page):
        expect(analytics_page.get_by_text("Top products", exact=True)).to_be_visible()
        expect(analytics_page.get_by_role("columnheader", name="Product", exact=True)).to_be_visible()
        for col in ["Impressions", "Interactions"]:
            expect(analytics_page.get_by_role("columnheader", name=col).first).to_be_visible()

    def test_top_users_table(self, analytics_page: Page):
        expect(analytics_page.get_by_text("Top Users", exact=True)).to_be_visible()
        for col in ["Name", "Age", "Level", "Scans"]:
            expect(analytics_page.get_by_role("columnheader", name=col, exact=True)).to_be_visible()

    def test_review_interactions(self, analytics_page: Page):
        expect(analytics_page.get_by_text("Review Interactions", exact=True)).to_be_visible()

    def test_competitors_ads_table(self, analytics_page: Page):
        expect(analytics_page.get_by_text("Competitors Ads", exact=True)).to_be_visible()
        for col in ["Competitors Product", "Ads Impressions", "Ad Clicks",
                     "Users", "Conversions %", "Product Page Interactions"]:
            expect(analytics_page.get_by_role("columnheader", name=col, exact=True)).to_be_visible()

    def test_competitors_ads_radio_toggle(self, analytics_page: Page):
        radiogroup = analytics_page.get_by_role("radiogroup")
        expect(radiogroup).to_be_visible()
        expect(radiogroup.get_by_text("Ads", exact=True)).to_be_visible()
        expect(radiogroup.get_by_text("Products", exact=True)).to_be_visible()

    def test_toolbar_buttons(self, analytics_page: Page):
        add_btn = analytics_page.get_by_role("button", name="Add widgets")
        expect(add_btn).to_be_visible()
        expect(add_btn).to_be_enabled()

        export_btn = analytics_page.locator("button").filter(has_text="Export")
        expect(export_btn).to_be_visible()
        expect(export_btn).to_be_enabled()

    def test_no_loading_spinners(self, analytics_page: Page):
        spinners = analytics_page.locator(
            "[class*='spinner'], [aria-busy='true'], [class*='skeleton']"
        )
        for i in range(spinners.count()):
            expect(spinners.nth(i)).not_to_be_visible()

    def test_no_rendering_errors(self, analytics_page: Page):
        body_text = analytics_page.inner_text("body")
        for bad in ["NaN", "undefined"]:
            assert bad not in body_text, f"'{bad}' found on page"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FILTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceFilters:

    def test_filter_defaults(self, analytics_page: Page):
        date_pattern = re.compile(r"\d{2}/\d{2}/\d{4}")
        inputs = analytics_page.locator("input")
        found_dates = [
            inputs.nth(i).input_value()
            for i in range(inputs.count())
            if date_pattern.match(inputs.nth(i).input_value())
        ]
        assert len(found_dates) >= 2, f"Expected 2 date inputs, got: {found_dates}"

        expect(analytics_page.get_by_text("Daily").first).to_be_visible()
        expect(analytics_page.get_by_text("Australia").first).to_be_visible()
        expect(analytics_page.get_by_text("All brands").first).to_be_visible()
        expect(analytics_page.locator("text=All GTIN's").first).to_be_visible()

    def test_granularity_dropdown_opens(self, analytics_page: Page):
        analytics_page.get_by_text("Daily").first.click(force=True)
        analytics_page.wait_for_timeout(600)
        body_html = analytics_page.content()
        assert any(w in body_html for w in ["Weekly", "Monthly"]), \
            "Granularity dropdown did not show options"
        analytics_page.keyboard.press("Escape")

    def test_country_dropdown_opens(self, analytics_page: Page):
        analytics_page.get_by_text("Australia").first.click(force=True)
        analytics_page.wait_for_timeout(600)
        options = analytics_page.locator("[class*='option'], [role='option'], li").first
        expect(options).to_be_visible(timeout=5_000)
        analytics_page.keyboard.press("Escape")

    def test_radio_toggle_switches(self, analytics_page: Page):
        radiogroup = analytics_page.get_by_role("radiogroup")
        products_radio = radiogroup.get_by_role("radio", name="Products")
        ads_radio = radiogroup.get_by_role("radio", name="Ads")

        expect(products_radio).to_be_checked()
        expect(ads_radio).not_to_be_checked()

        radiogroup.get_by_text("Ads", exact=True).click()
        analytics_page.wait_for_timeout(400)
        expect(ads_radio).to_be_checked()

        radiogroup.get_by_text("Products", exact=True).click()
        analytics_page.wait_for_timeout(400)
        expect(products_radio).to_be_checked()

    def test_date_change_triggers_api(self, page: Page):
        page.goto(ANALYTICS_PERF_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("h3:has-text('Reach')", timeout=20_000)

        daily_chart = page.get_by_text("Daily Engagement", exact=True)
        daily_chart.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        inputs = page.locator("input")
        start_input = next(
            (inputs.nth(i) for i in range(inputs.count())
             if re.match(r"\d{2}/\d{2}/\d{4}", inputs.nth(i).input_value())),
            None
        )
        if start_input is None:
            pytest.skip("Could not locate date input")

        def _is_daily_engagement_response(resp) -> bool:
            if resp.url != GRAPHQL_URL or resp.request.method != "POST":
                return False
            try:
                return bool(re.search(r'"(?:day|hasDay)"\s*:\s*true', resp.text()))
            except Exception:
                return False

        with page.expect_response(_is_daily_engagement_response, timeout=15_000) as resp_info:
            start_input.click(click_count=3)
            start_input.type("01/01/2026")
            page.keyboard.press("Tab")

        response = resp_info.value
        assert response.status == 200
        body = response.json()
        assert "data" in body or "errors" in body


# ═══════════════════════════════════════════════════════════════════════════════
# 3. API / BE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceAPI:

    def test_api_health(self, page: Page):
        session_ok = []
        countries_ok = []
        brands_ok = []
        gql_bodies = []
        gql_fails = []

        def handle_response(resp):
            if "identity-service/session" in resp.url:
                session_ok.append(resp.status)
            elif "settings-service/countries" in resp.url:
                countries_ok.append(resp.status)
            elif "participant-service/v2/brands/global/list" in resp.url:
                brands_ok.append(resp.status)
            elif resp.url == GRAPHQL_URL:
                if resp.status not in (200, 304):
                    gql_fails.append(resp.status)
                else:
                    try:
                        gql_bodies.append(resp.json())
                    except Exception:
                        pass

        page.on("response", handle_response)
        page.goto(BASE_URL + "/admin")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("text=Dashboard", timeout=15_000)
        page.goto(ANALYTICS_PERF_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("h3:has-text('Reach')", timeout=20_000)
        page.remove_listener("response", handle_response)

        assert session_ok and all(s == 200 for s in session_ok)
        assert countries_ok and all(s == 200 for s in countries_ok)
        assert brands_ok and all(s == 200 for s in brands_ok)
        assert len(gql_bodies) >= 4
        assert gql_fails == []
        for body in gql_bodies:
            assert "data" in body or "errors" in body

    def test_request_contains_dates(self, analytics_page: Page):
        payloads = capture_requests(
            analytics_page,
            lambda: set_date_range(analytics_page, *FULL_RANGE),
        )
        assert payloads, "No request payloads captured"
        combined = json.dumps(payloads)
        assert any(p in combined for p in ["2026-01-01", "01/01/2026"]), \
            "Start date not found in request"
        assert any(p in combined for p in ["2026-04-04", "04/04/2026"]), \
            "End date not found in request"

    def test_multiple_widget_queries_fire(self, analytics_page: Page):
        bodies = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *FULL_RANGE),
        )
        assert len(bodies) >= 3, f"Expected ≥3 responses, got {len(bodies)}"

    def test_no_graphql_errors(self, analytics_page: Page):
        bodies = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *FULL_RANGE),
        )
        errors_found = [b["errors"] for b in bodies if b.get("errors")]
        assert not errors_found, f"GraphQL errors: {errors_found}"

    def test_daily_engagement_fields(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        eng = get_daily_engagement(bodies)
        assert eng, "No daily engagement records"
        required = {"day", "month", "year", "impressions", "scans", "clicks", "reviews", "video_views"}
        for record in eng:
            missing = required - set(record.keys())
            assert not missing, f"Missing fields {missing}"

    def test_top_products_fields(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        prods = get_top_products(bodies)
        assert prods, "No top products"
        required = {"product_name", "impressions", "interactions"}
        for p in prods:
            missing = required - set(p.keys())
            assert not missing, f"Missing fields {missing}"

    def test_top_users_fields(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        users = get_top_users(bodies)
        assert users, "No top users"
        required = {"name", "age", "level", "scans"}
        for u in users:
            missing = required - set(u.keys())
            assert not missing, f"Missing fields {missing}"

    def test_all_numeric_fields_non_negative(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        eng = get_daily_engagement(bodies)
        for record in eng:
            for field in ["impressions", "scans", "clicks", "reviews", "video_views"]:
                assert record.get(field, 0) >= 0, \
                    f"Negative '{field}' on {record.get('year')}-{record.get('month')}-{record.get('day')}"

    # ── Data sync gap ────────────────────────────────────────────────────────

    def test_first_record_matches_start_date(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        eng = get_daily_engagement(bodies)
        assert eng, "No daily engagement records"
        first = eng[0]
        assert (first["year"], first["month"], first["day"]) == (2026, 1, 1)

    def test_last_record_close_to_end_date(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        eng = get_daily_engagement(bodies)
        assert eng, "No daily engagement records"
        last_date = datetime.date(eng[-1]["year"], eng[-1]["month"], eng[-1]["day"])
        end_date = parse_mmddyyyy(FULL_RANGE[1])
        gap = (end_date - last_date).days
        assert 0 <= gap <= 3, f"Data sync gap: last record {last_date}, end date {end_date} ({gap} days)"

    def test_no_missing_days(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        eng = get_daily_engagement(bodies)
        assert eng, "No daily engagement records"
        first_date = datetime.date(eng[0]["year"], eng[0]["month"], eng[0]["day"])
        last_date = datetime.date(eng[-1]["year"], eng[-1]["month"], eng[-1]["day"])
        expected = (last_date - first_date).days + 1
        assert len(eng) == expected, \
            f"Expected {expected} records ({first_date}→{last_date}), got {len(eng)}"

    def test_last_record_has_real_data(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        eng = get_daily_engagement(bodies)
        assert eng, "No daily engagement records"
        last = eng[-1]
        assert any(last.get(f, 0) > 0 for f in ["impressions", "scans", "clicks", "reviews", "video_views"]), \
            f"Last record all zeros: {last}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. FE/BE CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceBEvsUI:

    def test_top_product_name_matches_api(self, session_page: Page):
        """The #1 product name from the API must match the #1 row in the UI table.

        Navigate OUTSIDE the capture window so the initial page-load response
        (default date range) is not mixed in with the FULL_RANGE response.
        The Top Products table uses Ant Design's split-table layout:
          table[0] = thead only, table[1] = tbody (row 0 = header, row 1+ = data)
        """
        session_page.goto(ANALYTICS_PERF_URL)
        _flush(session_page)
        bodies = capture_responses(
            session_page,
            lambda: (set_date_range(session_page, *FULL_RANGE), _flush(session_page)),
        )
        prods = get_top_products(bodies)
        assert prods, "No top products in API response"
        api_top_name = prods[0]["product_name"]
        assert api_top_name, "Top product has empty name in API"

        session_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        session_page.wait_for_timeout(1_000)
        first_data_row = session_page.locator("table").nth(1).locator("tbody tr").nth(1)
        expect(first_data_row).to_be_visible(timeout=15_000)
        ui_top_name = first_data_row.locator("td").first.inner_text().strip()

        assert ui_top_name == api_top_name, (
            f"FE/BE mismatch on Top Products #1:\n"
            f"  API returned : '{api_top_name}'\n"
            f"  UI is showing: '{ui_top_name}'\n"
            f"The UI may be rendering a different date range than what was queried."
        )

    def test_top_products_sorted_by_interactions(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        prods = get_top_products(bodies)
        assert len(prods) >= 2
        interactions = [p["interactions"] for p in prods]
        assert interactions == sorted(interactions, reverse=True)

    def test_top_users_sorted_by_scans(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        users = get_top_users(bodies)
        assert len(users) >= 2
        scans = [u["scans"] for u in users]
        assert scans == sorted(scans, reverse=True)

    def test_no_data_beyond_last_api_record(self, session_page: Page):
        bodies = capture_responses(
            session_page,
            lambda: fresh_load(session_page, *FULL_RANGE),
        )
        eng = get_daily_engagement(bodies)
        assert eng
        body_text = session_page.inner_text("body")
        for bad in ["NaN", "undefined"]:
            assert bad not in body_text, f"'{bad}' found — chart may render beyond API data"

    def test_no_data_placeholder_hidden_when_data_exists(self, session_page: Page):
        fresh_load(session_page, *FULL_RANGE)
        no_data = session_page.locator("text=/No [Dd]ata/").first
        if no_data.count() > 0:
            expect(no_data).not_to_be_visible(timeout=5_000)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. AGGREGATION CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceAggregation:

    def _click_granularity(self, page: Page, label: str) -> list[dict]:
        bodies: list[dict] = []

        def on_response(resp):
            if resp.url == GRAPHQL_URL and resp.status == 200:
                try:
                    bodies.append(resp.json())
                except Exception:
                    pass

        def _has_engagements(resp) -> bool:
            if resp.url != GRAPHQL_URL or resp.status != 200:
                return False
            try:
                eng = resp.json().get("data", {}).get("analytics", {}).get("engagements", [])
                return len(eng) > 0
            except Exception:
                return False

        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass

        page.on("response", on_response)

        with page.expect_response(_has_engagements, timeout=30_000):
            page.evaluate("""() => {
                const items = document.querySelectorAll('.ant-select-selection-item');
                for (const item of items) {
                    if (['Daily', 'Weekly', 'Monthly'].includes(item.textContent.trim())) {
                        const selector = item.closest('.ant-select-selector') || item;
                        selector.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true}));
                        selector.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true}));
                        return;
                    }
                }
            }""")
            page.wait_for_timeout(400)

            page.evaluate(f"""() => {{
                const option = document.querySelector('.ant-select-item-option[title="{label}"]');
                if (option) {{
                    option.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true}}));
                }}
            }}""")

        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        page.wait_for_timeout(2_000)

        page.remove_listener("response", on_response)
        return bodies

    def test_monthly_impressions_match_daily_sum(self, analytics_page: Page):
        daily_bodies = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *FULL_RANGE),
        )
        daily_eng = get_daily_engagement(daily_bodies)
        assert daily_eng, "No daily records"

        daily_sum_by_month: dict[int, int] = {}
        for r in daily_eng:
            m = r["month"]
            daily_sum_by_month[m] = daily_sum_by_month.get(m, 0) + r.get("impressions", 0)

        monthly_bodies = self._click_granularity(analytics_page, "Monthly")
        monthly_eng: list[dict] = []
        for b in monthly_bodies:
            eng = b.get("data", {}).get("analytics", {}).get("engagements", [])
            if eng:
                monthly_eng = eng
                break

        if not monthly_eng:
            pytest.skip("Monthly engagement records not captured")

        monthly_api_by_month: dict[int, int] = {}
        for r in monthly_eng:
            m = r.get("month")
            if m is not None:
                monthly_api_by_month[m] = monthly_api_by_month.get(m, 0) + r.get("impressions", 0)

        mismatches = []
        for m, api_sum in monthly_api_by_month.items():
            if m in daily_sum_by_month and api_sum != daily_sum_by_month[m]:
                mismatches.append(f"Month {m}: monthly={api_sum}, daily sum={daily_sum_by_month[m]}")

        assert not mismatches, "Monthly vs daily mismatch:\n" + "\n".join(mismatches)
        self._click_granularity(analytics_page, "Daily")

    def test_weekly_impressions_match_daily_sum(self, analytics_page: Page):
        daily_bodies = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *FULL_RANGE),
        )
        daily_eng = get_daily_engagement(daily_bodies)
        assert daily_eng, "No daily records"

        daily_sum_by_week: dict[int, int] = {}
        for r in daily_eng:
            d = datetime.date(r["year"], r["month"], r["day"])
            week = d.isocalendar()[1]
            daily_sum_by_week[week] = daily_sum_by_week.get(week, 0) + r.get("impressions", 0)

        weekly_bodies = self._click_granularity(analytics_page, "Weekly")
        weekly_eng: list[dict] = []
        for b in weekly_bodies:
            eng = b.get("data", {}).get("analytics", {}).get("engagements", [])
            if eng and "week" in eng[0]:
                weekly_eng = eng
                break

        if not weekly_eng:
            pytest.skip("Weekly engagement records not captured")

        weekly_api_by_week: dict[int, int] = {}
        for r in weekly_eng:
            w = r.get("week")
            if w is not None:
                weekly_api_by_week[w] = weekly_api_by_week.get(w, 0) + r.get("impressions", 0)

        mismatches = []
        for w, api_sum in weekly_api_by_week.items():
            if w in daily_sum_by_week and api_sum != daily_sum_by_week[w]:
                mismatches.append(f"Week {w}: weekly={api_sum}, daily sum={daily_sum_by_week[w]}")

        assert not mismatches, "Weekly vs daily mismatch:\n" + "\n".join(mismatches)
        self._click_granularity(analytics_page, "Daily")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DATE CHANGE → RESULTS CHANGE
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceDateChange:

    def test_different_ranges_different_impressions(self, analytics_page: Page):
        bodies_a = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *RANGE_A),
        )
        total_a = sum(r.get("impressions", 0) for r in get_daily_engagement(bodies_a))
        _flush(analytics_page)
        bodies_b = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *RANGE_B),
        )
        total_b = sum(r.get("impressions", 0) for r in get_daily_engagement(bodies_b))
        assert total_a != total_b, \
            f"Both ranges returned same impressions ({total_a})"

    def test_different_ranges_correct_months(self, analytics_page: Page):
        bodies_a = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *RANGE_A),
        )
        eng_a = get_daily_engagement(bodies_a)
        assert eng_a and eng_a[0]["month"] == 1
        _flush(analytics_page)
        bodies_b = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *RANGE_B),
        )
        eng_b = get_daily_engagement(bodies_b)
        assert eng_b and eng_b[0]["month"] == 3

    def test_different_ranges_different_top_products(self, analytics_page: Page):
        bodies_a = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *RANGE_A),
        )
        prods_a = get_top_products(bodies_a)
        _flush(analytics_page)
        bodies_b = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *RANGE_B),
        )
        prods_b = get_top_products(bodies_b)
        if not prods_a or not prods_b:
            pytest.skip("One range returned no products")
        assert prods_a[0]["interactions"] != prods_b[0]["interactions"], \
            f"Top product interactions identical ({prods_a[0]['interactions']})"

    def test_narrower_range_fewer_records(self, analytics_page: Page):
        bodies_full = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *FULL_RANGE),
        )
        count_full = len(get_daily_engagement(bodies_full))
        _flush(analytics_page)
        bodies_jan = capture_responses(
            analytics_page,
            lambda: set_date_range(analytics_page, *RANGE_A),
        )
        count_jan = len(get_daily_engagement(bodies_jan))
        assert count_jan < count_full, \
            f"January ({count_jan}) not fewer than full range ({count_full})"
