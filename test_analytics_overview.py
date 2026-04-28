"""
test_analytics_overview.py
Tests for Shping Admin — Analytics > Overview tab
(URL: /admin/analytics/roi)

Classes:
  1. TestLoginPage        — unauthenticated login flow
  2. TestPageLoadAndNav   — page load, sidebar, tab navigation
  3. TestOverviewRender   — widget / KPI visibility on the Overview tab
  4. TestOverviewDateRange — date filter fires correct GraphQL requests
  5. TestOverviewAPI      — GraphQL response structure and data quality
  6. TestOverviewBEvsUI   — UI values match API values

Run:
    pytest test_analytics_overview.py -v --headed
"""

import re
import json
import datetime
import pytest
from playwright.sync_api import Page, expect

from conftest import (
    ANALYTICS_PERF_URL,
    ANALYTICS_ROI_URL,
    BASE_URL,
    LOGIN_URL,
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    API_BASE_URL,
)

GRAPHQL_URL = f"{API_BASE_URL}/graphql"

_today     = datetime.date.today()
_start     = datetime.date(_today.year, 1, 1)
FULL_RANGE = (_start.strftime("%m/%d/%Y"), _today.strftime("%m/%d/%Y"))
RANGE_A    = ("01/01/2026", "01/31/2026")   # January only
RANGE_B    = ("03/01/2026", "03/31/2026")   # March only


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
        pytest.skip("Date picker inputs not found — page may not have loaded")

    date_inputs[0].click(click_count=3)
    date_inputs[0].type(start)
    page.keyboard.press("Tab")
    date_inputs[1].click(click_count=3)
    date_inputs[1].type(end)
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")

    page.evaluate("window.scrollBy(0, 600)")
    page.wait_for_timeout(500)
    try:
        page.wait_for_load_state("networkidle", timeout=12_000)
    except Exception:
        pass
    page.wait_for_timeout(3_000)


def capture_requests(page: Page, action_fn) -> list[dict]:
    """Capture GraphQL POST request payloads sent by the browser."""
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
    """Capture GraphQL response bodies returned by the server."""
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


def _flush(page: Page) -> None:
    """Wait for in-flight requests to settle."""
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass
    page.wait_for_timeout(3_000)


def _goto_roi(page: Page) -> None:
    """Navigate to the Overview (ROI) tab and wait for content."""
    page.goto(ANALYTICS_ROI_URL)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass
    page.wait_for_timeout(2_000)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOGIN PAGE (unauthenticated)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginPage:

    def test_login_form_elements(self, unauth_page: Page):
        unauth_page.goto(LOGIN_URL)
        unauth_page.wait_for_load_state("networkidle")
        expect(unauth_page.get_by_role("textbox", name="you@domain.com")).to_be_visible()
        expect(unauth_page.get_by_role("textbox", name="Your password")).to_be_visible()
        login_btn = unauth_page.get_by_role("button", name="Login")
        expect(login_btn).to_be_visible()
        expect(login_btn).to_be_disabled()

    def test_login_flow(self, unauth_page: Page):
        unauth_page.goto(LOGIN_URL)
        unauth_page.wait_for_load_state("networkidle")
        unauth_page.get_by_role("textbox", name="you@domain.com").fill(ADMIN_EMAIL)
        unauth_page.get_by_role("textbox", name="Your password").fill(ADMIN_PASSWORD)
        unauth_page.get_by_role("button", name="Login").click()
        unauth_page.wait_for_url(lambda url: "/admin" in url, timeout=20_000)
        expect(unauth_page).to_have_url(re.compile(r"/admin"))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PAGE LOAD & NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestPageLoadAndNav:

    def test_page_load(self, analytics_page: Page):
        """Performance tab (default landing) loads and shows the Dashboard link."""
        expect(analytics_page).to_have_url(re.compile(r"/admin/analytics/overview"))
        expect(analytics_page).to_have_title(re.compile(r"Shping", re.IGNORECASE))
        expect(analytics_page.get_by_text("Dashboard", exact=True)).to_be_visible()

    def test_sidebar_nav_items(self, analytics_page: Page):
        expect(analytics_page.get_by_role("heading", name="Main Menu")).to_be_visible()
        for item in ["Analytics", "Media Hub", "Loyalty Hub", "Settings"]:
            expect(analytics_page.get_by_role("link", name=item)).to_be_visible()
        expect(analytics_page.get_by_role("link", name="Sign out")).to_be_visible()

    def test_analytics_subtabs(self, analytics_page: Page):
        for tab in ["Overview", "Performance", "Audience", "Geography",
                    "Conversion", "Spend", "Insights"]:
            expect(analytics_page.get_by_role("link", name=tab)).to_be_visible()

    def test_tab_navigation_to_overview(self, analytics_page: Page):
        """Clicking 'Overview' tab navigates to /analytics/roi."""
        analytics_page.get_by_role("link", name="Overview").click()
        analytics_page.wait_for_url(re.compile(r"/analytics/roi"), timeout=10_000)
        expect(analytics_page).to_have_url(re.compile(r"/analytics/roi"))

    def test_tab_navigation_back_to_performance(self, analytics_page: Page):
        """Clicking 'Performance' tab after Overview navigates back to /analytics/overview."""
        analytics_page.get_by_role("link", name="Overview").click()
        analytics_page.wait_for_url(re.compile(r"/analytics/roi"), timeout=10_000)
        analytics_page.get_by_role("link", name="Performance").click()
        analytics_page.wait_for_url(re.compile(r"/analytics/overview"), timeout=10_000)
        expect(analytics_page).to_have_url(re.compile(r"/analytics/overview"))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. OVERVIEW TAB — RENDER
# ═══════════════════════════════════════════════════════════════════════════════

class TestOverviewRender:
    """Checks that the Overview/ROI tab page renders correctly."""

    def test_page_loads_at_roi_url(self, session_page: Page):
        """Overview tab must open at /analytics/roi."""
        _goto_roi(session_page)
        expect(session_page).to_have_url(re.compile(r"/analytics/roi"))

    def test_date_picker_present(self, session_page: Page):
        """Two date inputs (start / end) must be present on the Overview page."""
        _goto_roi(session_page)
        inputs = session_page.locator("input")
        date_inputs = [
            inputs.nth(i)
            for i in range(inputs.count())
            if re.match(r"\d{2}/\d{2}/\d{4}", inputs.nth(i).input_value())
        ]
        assert len(date_inputs) >= 2, (
            f"Expected ≥2 date inputs on Overview tab, found {len(date_inputs)}"
        )

    def test_no_rendering_errors(self, session_page: Page):
        """'NaN' and 'undefined' must not appear anywhere on the Overview page."""
        _goto_roi(session_page)
        body_text = session_page.inner_text("body")
        for bad in ["NaN", "undefined"]:
            assert bad not in body_text, (
                f"'{bad}' found on Overview page — a widget may have failed to render"
            )

    def test_no_loading_spinners_after_load(self, session_page: Page):
        """All loading spinners must be gone once the page has settled."""
        _goto_roi(session_page)
        spinners = session_page.locator(
            "[class*='spinner'], [aria-busy='true'], [class*='skeleton']"
        )
        for i in range(spinners.count()):
            expect(spinners.nth(i)).not_to_be_visible()

    def test_numeric_values_visible_on_page(self, session_page: Page):
        """At least one numeric value must appear somewhere on the Overview page."""
        _goto_roi(session_page)
        body_text = session_page.inner_text("body")
        assert re.search(r"\d+", body_text), (
            "No numeric values found on Overview page — widgets may not have loaded"
        )

    def test_export_button_visible(self, session_page: Page):
        """Export button must be visible on the Overview tab."""
        _goto_roi(session_page)
        export_btn = session_page.locator("button").filter(has_text="Export")
        expect(export_btn).to_be_visible()

    def test_add_widgets_button_visible(self, session_page: Page):
        """'Add widgets' button must be visible on the Overview tab."""
        _goto_roi(session_page)
        add_btn = session_page.get_by_role("button", name="Add widgets")
        expect(add_btn).to_be_visible()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. OVERVIEW TAB — DATE RANGE FILTER
# ═══════════════════════════════════════════════════════════════════════════════

class TestOverviewDateRange:
    """Checks that the date range filter on the Overview tab fires correct requests."""

    def test_date_change_fires_graphql(self, session_page: Page):
        """Changing the date range must trigger at least one GraphQL POST."""
        _goto_roi(session_page)
        with session_page.expect_request(
            lambda req: req.url == GRAPHQL_URL and req.method == "POST",
            timeout=15_000,
        ) as req_info:
            set_date_range(session_page, *FULL_RANGE)
        assert req_info.value is not None, \
            "No GraphQL POST fired after changing the date range on Overview tab"

    def test_request_contains_start_date(self, session_page: Page):
        """POST body must contain the selected start date."""
        _goto_roi(session_page)
        payloads = capture_requests(
            session_page,
            lambda: set_date_range(session_page, *FULL_RANGE),
        )
        assert payloads, "No request payloads captured on Overview tab"
        combined = json.dumps(payloads)
        start_iso = _start.strftime("%Y-%m-%d")
        assert any(p in combined for p in [start_iso, FULL_RANGE[0]]), (
            f"Start date not found in any request payload.\n{combined[:500]}"
        )

    def test_request_contains_end_date(self, session_page: Page):
        """POST body must contain the selected end date."""
        _goto_roi(session_page)
        payloads = capture_requests(
            session_page,
            lambda: set_date_range(session_page, *FULL_RANGE),
        )
        assert payloads, "No request payloads captured on Overview tab"
        combined = json.dumps(payloads)
        end_iso = _today.strftime("%Y-%m-%d")
        assert any(p in combined for p in [end_iso, FULL_RANGE[1]]), (
            f"End date not found in any request payload.\n{combined[:500]}"
        )

    def test_no_graphql_errors_after_date_change(self, session_page: Page):
        """No GraphQL response should carry a non-empty 'errors' array."""
        _goto_roi(session_page)
        bodies = capture_responses(
            session_page,
            lambda: set_date_range(session_page, *FULL_RANGE),
        )
        errors_found = [b["errors"] for b in bodies if b.get("errors")]
        assert not errors_found, \
            f"GraphQL errors returned on Overview tab:\n{json.dumps(errors_found[:2], indent=2)}"

    def test_multiple_queries_fire(self, session_page: Page):
        """At least one GraphQL response must be received when the date changes."""
        _goto_roi(session_page)
        bodies = capture_responses(
            session_page,
            lambda: set_date_range(session_page, *FULL_RANGE),
        )
        assert len(bodies) >= 7, (
            f"Expected ≥7 GraphQL response after date change on Overview tab, got {len(bodies)}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. OVERVIEW TAB — API RESPONSE QUALITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestOverviewAPI:
    """Checks that the GraphQL responses for the Overview tab have valid data."""

    def test_responses_have_data_key(self, session_page: Page):
        """Every GraphQL response must have a top-level 'data' key (no bare errors)."""
        _goto_roi(session_page)
        bodies = capture_responses(
            session_page,
            lambda: set_date_range(session_page, *FULL_RANGE),
        )
        assert bodies, "No responses captured for Overview tab"
        for b in bodies:
            assert "data" in b or "errors" in b, (
                f"Response has neither 'data' nor 'errors':\n{b}"
            )
            assert not b.get("errors"), (
                f"GraphQL error in Overview response:\n{b.get('errors')}"
            )

    def test_analytics_key_present_in_response(self, session_page: Page):
        """At least one response must contain data.analytics."""
        _goto_roi(session_page)
        bodies = capture_responses(
            session_page,
            lambda: set_date_range(session_page, *FULL_RANGE),
        )
        analytics_bodies = [
            b for b in bodies
            if b.get("data", {}).get("analytics") is not None
        ]
        assert analytics_bodies, (
            "No response contained data.analytics on Overview tab — "
            "the ROI query may use a different key"
        )

    def test_different_ranges_return_different_totals(self, session_page: Page):
        """January and March must return different aggregate values."""
        _goto_roi(session_page)
        bodies_a = capture_responses(
            session_page,
            lambda: set_date_range(session_page, *RANGE_A),
        )
        _flush(session_page)
        bodies_b = capture_responses(
            session_page,
            lambda: set_date_range(session_page, *RANGE_B),
        )

        def _extract_numbers(bodies):
            """Pull every integer/float out of all response payloads."""
            nums = []
            for b in bodies:
                for v in _flatten_values(b):
                    if isinstance(v, (int, float)) and v > 0:
                        nums.append(v)
            return nums

        nums_a = _extract_numbers(bodies_a)
        nums_b = _extract_numbers(bodies_b)
        if not nums_a or not nums_b:
            pytest.skip("Could not extract numeric values from Overview responses")
        assert nums_a != nums_b, (
            "Overview tab returned identical numeric values for Jan and Mar — "
            "date filter may not be affecting the query"
        )

    def test_no_graphql_errors_on_load(self, session_page: Page):
        """No GraphQL errors when Overview tab first loads."""
        bodies = capture_responses(session_page, lambda: _goto_roi(session_page))
        errors_found = [b["errors"] for b in bodies if b.get("errors")]
        assert not errors_found, \
            f"GraphQL errors on Overview page load:\n{json.dumps(errors_found[:2], indent=2)}"


def _flatten_values(obj, depth=0):
    """Recursively yield all leaf values from a nested dict/list."""
    if depth > 10:
        return
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten_values(v, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            yield from _flatten_values(item, depth + 1)
    else:
        yield obj


# ═══════════════════════════════════════════════════════════════════════════════
# 6. OVERVIEW TAB — FE/BE CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestOverviewBEvsUI:
    """Checks that the Overview tab UI reflects what the API returns."""

    def test_no_data_placeholder_hidden_when_api_returns_data(self, session_page: Page):
        """If the API returned data, the UI must NOT show a 'No Data' placeholder.
        This is a BE/FE consistency check: we first confirm the backend sent records,
        then verify the frontend is actually rendering them (not hiding behind a placeholder).
        """
        _goto_roi(session_page)
        bodies = capture_responses(
            session_page,
            lambda: set_date_range(session_page, *FULL_RANGE),
        )

        # BE side — check the API actually returned something
        api_has_data = any(
            b.get("data", {}).get("analytics") is not None
            for b in bodies
        )
        if not api_has_data:
            pytest.skip("API returned no analytics data for FULL_RANGE — cannot verify UI")

        # FE side — UI must not show 'No Data' since the API has data
        no_data = session_page.locator("text=/No [Dd]ata/").first
        if no_data.count() > 0:
            expect(no_data).not_to_be_visible(timeout=5_000), (
                "UI is showing 'No Data' even though the API returned records — "
                "the frontend may not be rendering the response correctly"
            )

    def test_date_range_change_updates_ui(self, session_page: Page):
        """Switching between RANGE_A and RANGE_B must produce visibly different page content."""
        _goto_roi(session_page)
        set_date_range(session_page, *RANGE_A)
        text_a = session_page.inner_text("body")

        _flush(session_page)
        set_date_range(session_page, *RANGE_B)
        text_b = session_page.inner_text("body")

        # The numeric values on the page should differ between the two months
        nums_a = set(re.findall(r"\b\d[\d,]*\b", text_a))
        nums_b = set(re.findall(r"\b\d[\d,]*\b", text_b))
        assert nums_a != nums_b, (
            "Page content (numbers) did not change when switching from Jan to Mar — "
            "Overview tab may not be re-fetching data on date change"
        )

    def test_wider_range_does_not_show_less_data_than_narrow(self, session_page: Page):
        """A wider date range must return at least as many data points as a narrow one."""
        _goto_roi(session_page)
        bodies_narrow = capture_responses(
            session_page,
            lambda: set_date_range(session_page, *RANGE_A),  # Jan only (31 days)
        )
        _flush(session_page)
        bodies_wide = capture_responses(
            session_page,
            lambda: set_date_range(session_page, *FULL_RANGE),  # Full year-to-date
        )

        def _total_records(bodies):
            total = 0
            for b in bodies:
                analytics = b.get("data", {}).get("analytics", {})
                for v in analytics.values():
                    if isinstance(v, list):
                        total += len(v)
            return total

        count_narrow = _total_records(bodies_narrow)
        count_wide   = _total_records(bodies_wide)
        if count_narrow == 0:
            pytest.skip("No list data found in Overview responses to compare")
        assert count_wide >= count_narrow, (
            f"BUG — wider date range returned fewer records ({count_wide}) "
            f"than narrow range ({count_narrow})"
        )
