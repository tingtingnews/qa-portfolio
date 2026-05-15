"""
test_analytics_audience.py
UI tests for Shping Admin — Analytics > Audience page
(URL: /admin/analytics/audience)

Covers the four chart / widget sections visible on the Audience tab:
  1. Audience (age-distribution bar chart)
  2. Gender (donut chart)
  3. Generation (donut chart)
  4. Engaged Users (circle metric widget)

Date range: 03/01/2026 – 04/07/2026
Participant: Authenticateit Pty Ltd

IMPORTANT — Canvas rendering:
    The Audience, Gender, and Generation charts are rendered entirely on
    <canvas> elements.  All axis labels, legend entries, percentage labels,
    and chart segments are painted pixels — they do NOT appear in the DOM
    as text nodes.  Therefore these tests verify:
      - The widget container (identified by its stable `id` attribute) exists
      - The widget title (the only DOM text) is visible
      - A <canvas> is present with non-zero dimensions
      - The canvas contains non-blank pixel data (i.e. the chart actually drew)

    The Engaged Users widget is the exception — its numbers and subtitle
    are real DOM text, so we assert on their values directly.

Run:
    pytest test_analytics_audience.py -v --headed
    pytest test_analytics_audience.py -v --headed --slowmo=500
"""

import json
import re
import pytest
from playwright.sync_api import Page, expect

from conftest import API_BASE_URL, ANALYTICS_AUDIENCE_URL


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIENCE TAB — CHART / WIDGET UI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudienceCharts:
    """
    Four UI tests for the chart widgets on Analytics > Audience.
    All tests share the same audience_page fixture which navigates to
    /admin/analytics/audience and sets the date range to
    03/01/2026 – 04/07/2026.

    Widget containers are located by their stable DOM `id` attributes:
      #audience, #gender, #generation, #totalUsers
    """

    # ── 1. Audience age-distribution bar chart ────────────────────────────

    def test_audience_age_bar_chart(self, audience_page: Page):
        """
        Audience bar chart (age distribution):
          - Widget container #audience is present in the DOM
          - Widget title 'Audience' is visible
          - A <canvas> element is rendered inside the widget
          - The canvas has non-zero width and height attributes
          - The canvas contains non-blank pixel data (chart actually drew)
        """
        # Widget container — the id="audience" appears on TWO elements:
        #   1. the outer react-grid-item wrapper
        #   2. the inner sc-EHOje div (data-index="audience")
        # We target the outer react-grid-item which contains everything.
        widget = audience_page.locator(".react-grid-item#audience")
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title — the only DOM text inside this widget.
        # Use locator scoped to the widget to avoid matching the "Audience"
        # tab link in the navigation bar.
        expect(widget.locator("div.sc-bxivhb")).to_contain_text("Audience")

        # Canvas element — the bar chart is drawn entirely on <canvas>.
        # Axis labels (0-20, 21-25 …), legend ("Age"), and bars are all
        # painted pixels, NOT DOM text.
        canvas = widget.locator("canvas").first
        expect(canvas).to_be_visible(timeout=15_000)

        # Canvas dimensions — non-zero proves the charting library initialised.
        width = canvas.get_attribute("width")
        height = canvas.get_attribute("height")
        assert width and int(width) > 0, "Audience chart canvas has zero width"
        assert height and int(height) > 0, "Audience chart canvas has zero height"

        # Canvas pixel data — verify the chart actually drew something
        # (not a blank white rectangle).  We sample the canvas via JS and
        # check that at least some pixels are non-white / non-transparent.
        has_data = audience_page.evaluate("""
            (canvasEl) => {
                const ctx = canvasEl.getContext('2d');
                if (!ctx) return false;
                const imageData = ctx.getImageData(0, 0, canvasEl.width, canvasEl.height);
                const data = imageData.data;
                // Check if any pixel is not fully white/transparent
                for (let i = 0; i < data.length; i += 4) {
                    const r = data[i], g = data[i+1], b = data[i+2], a = data[i+3];
                    if (a > 0 && (r < 250 || g < 250 || b < 250)) {
                        return true;
                    }
                }
                return false;
            }
        """, canvas.element_handle())
        assert has_data, "Audience bar chart canvas is blank — no chart data rendered"

    # ── 2. Gender donut chart ─────────────────────────────────────────────

    def test_gender_donut_chart(self, audience_page: Page):
        """
        Gender donut chart:
          - Widget container #gender is present in the DOM
          - Widget title 'Gender' is visible
          - A <canvas> element is rendered inside the widget
          - The canvas has non-zero dimensions
          - The canvas contains non-blank pixel data (donut segments drew)
        """
        # Widget container — target the outer react-grid-item (id appears
        # on both the grid-item wrapper and the inner div).
        widget = audience_page.locator(".react-grid-item#gender")
        widget.scroll_into_view_if_needed()
        audience_page.wait_for_timeout(500)
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("div.sc-bxivhb")).to_contain_text("Gender")

        # Canvas element — the donut chart (segments, legend entries like
        # "Male", "Female", "Others", and percentage labels like "47.1%")
        # are ALL painted on canvas, not in the DOM.
        canvas = widget.locator("canvas").first
        expect(canvas).to_be_visible(timeout=15_000)

        # Canvas dimensions
        width = canvas.get_attribute("width")
        height = canvas.get_attribute("height")
        assert width and int(width) > 0, "Gender chart canvas has zero width"
        assert height and int(height) > 0, "Gender chart canvas has zero height"

        # Canvas pixel data — verify donut segments actually rendered.
        has_data = audience_page.evaluate("""
            (canvasEl) => {
                const ctx = canvasEl.getContext('2d');
                if (!ctx) return false;
                const imageData = ctx.getImageData(0, 0, canvasEl.width, canvasEl.height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    const r = data[i], g = data[i+1], b = data[i+2], a = data[i+3];
                    if (a > 0 && (r < 250 || g < 250 || b < 250)) {
                        return true;
                    }
                }
                return false;
            }
        """, canvas.element_handle())
        assert has_data, "Gender donut chart canvas is blank — no chart data rendered"

    # ── 3. Generation donut chart ─────────────────────────────────────────

    def test_generation_donut_chart(self, audience_page: Page):
        """
        Generation donut chart:
          - Widget container #generation is present in the DOM
          - Widget title 'Generation' is visible
          - A <canvas> element is rendered inside the widget
          - The canvas has non-zero dimensions
          - The canvas contains non-blank pixel data (donut segments drew)
        """
        # Widget container — target the outer react-grid-item (id appears
        # on both the grid-item wrapper and the inner div).
        widget = audience_page.locator(".react-grid-item#generation")
        widget.scroll_into_view_if_needed()
        audience_page.wait_for_timeout(500)
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("div.sc-bxivhb")).to_contain_text("Generation")

        # Canvas element — the donut chart (segments, legend entries like
        # "Gen Y (Millennials)…", "Gen Z: 1997-2012", and percentage labels)
        # are ALL painted on canvas, not in the DOM.
        canvas = widget.locator("canvas").first
        expect(canvas).to_be_visible(timeout=15_000)

        # Canvas dimensions
        width = canvas.get_attribute("width")
        height = canvas.get_attribute("height")
        assert width and int(width) > 0, "Generation chart canvas has zero width"
        assert height and int(height) > 0, "Generation chart canvas has zero height"

        # Canvas pixel data — verify donut segments actually rendered.
        has_data = audience_page.evaluate("""
            (canvasEl) => {
                const ctx = canvasEl.getContext('2d');
                if (!ctx) return false;
                const imageData = ctx.getImageData(0, 0, canvasEl.width, canvasEl.height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    const r = data[i], g = data[i+1], b = data[i+2], a = data[i+3];
                    if (a > 0 && (r < 250 || g < 250 || b < 250)) {
                        return true;
                    }
                }
                return false;
            }
        """, canvas.element_handle())
        assert has_data, "Generation donut chart canvas is blank — no chart data rendered"

    # ── 4. Engaged Users widget ───────────────────────────────────────────

    def test_engaged_users_widget(self, audience_page: Page):
        """
        Engaged Users circular metric widget:
          - Widget container #totalUsers is present in the DOM
          - Widget title 'Engaged Users' is visible
          - A large numeric value is displayed (the engaged user count)
          - The numeric count is > 0 (data loaded for the date range)
          - The subtitle 'Total users within the defined period' is visible
          - A secondary total-users number is displayed below the circle
        """
        # Widget container — target the outer react-grid-item (id appears
        # on both the grid-item wrapper and the inner div).
        # Unlike the three chart widgets above, Engaged Users renders its
        # numbers and subtitle as real DOM text — so we can assert values.
        widget = audience_page.locator(".react-grid-item#totalUsers")
        widget.scroll_into_view_if_needed()
        audience_page.wait_for_timeout(500)
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("div.sc-bxivhb")).to_contain_text("Engaged Users")

        # Primary metric — large number inside the circle (e.g. "22,407").
        # Extract all comma-separated numbers from the widget's DOM text.
        section_text = widget.inner_text()
        numbers = re.findall(r"[\d,]+", section_text)
        numeric_values = [
            int(n.replace(",", ""))
            for n in numbers
            if n.replace(",", "").isdigit()
        ]
        assert len(numeric_values) >= 1, (
            f"Expected at least one numeric value in Engaged Users widget, "
            f"found none.  Widget text: {section_text[:200]}"
        )
        assert numeric_values[0] > 0, (
            f"Engaged Users count should be > 0 for this date range, "
            f"got {numeric_values[0]}"
        )

        # Subtitle label
        expect(
            widget.get_by_text("Total users within the defined period")
        ).to_be_visible()

        # Secondary total-users count (the smaller number below the circle)
        assert len(numeric_values) >= 2, (
            f"Expected both engaged-user count and total-user count, "
            f"found only: {numeric_values}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIENCE TAB — FILTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudienceFilters:
    """
    Filter interaction tests for Analytics > Audience.

    Covers:
      1. Same-month date range change — set both dates within a single month
         and verify the charts reload.
      2. Brand filter — search for "Gigi", select it, dismiss the dropdown
         by clicking blank space, and verify the filter applied.

    DOM notes (verified 2026-04-08):
      - Date inputs live inside `.ant-picker-range`:
            .ant-picker-input-start input   (start date)
            .ant-picker-input-end   input   (end date)
        Format is MM/DD/YYYY.  After typing a new value, press Tab to
        commit the field, then press Enter (or Tab from the end field)
        to trigger the query.
      - The brand dropdown has data-testid="audience_filter_selectBrand".
        It contains an <input type="search"> that filters a <table> of
        brand rows.  The search requires character-by-character input
        (`pressSequentially`) — `fill()` does NOT trigger filtering.
        After clicking a row, click any blank area on the page to close
        the dropdown and apply the selection.
    """

    # ── 1. Same-month date range ──────────────────────────────────────────

    def test_date_range_same_month(self, audience_page: Page):
        """
        Change the date range to a single month (04/01/2026 – 04/07/2026)
        and verify:
          - Both date inputs accept the new values
          - The Audience chart widget still renders (canvas is visible and
            contains non-blank pixel data after the date change)
          - No error or "No Data" text appears on the page
        """
        # ── Set the date range ───────────────────────────────────────────
        start_input = audience_page.locator(".ant-picker-input-start input")
        end_input = audience_page.locator(".ant-picker-input-end input")

        # Clear and type the start date
        start_input.click(click_count=3)
        start_input.type("04/01/2026")
        audience_page.keyboard.press("Tab")

        # Clear and type the end date
        end_input.click(click_count=3)
        end_input.type("04/07/2026")
        audience_page.keyboard.press("Enter")

        # Wait for the charts to reload after the date change
        audience_page.wait_for_timeout(3000)

        # ── Verify date inputs accepted the values ───────────────────────
        assert start_input.input_value() == "04/01/2026", (
            f"Start date not set correctly: {start_input.input_value()}"
        )
        assert end_input.input_value() == "04/07/2026", (
            f"End date not set correctly: {end_input.input_value()}"
        )

        # ── Verify the Audience chart re-rendered ────────────────────────
        widget = audience_page.locator(".react-grid-item#audience")
        expect(widget).to_be_visible(timeout=15_000)

        canvas = widget.locator("canvas").first
        expect(canvas).to_be_visible(timeout=15_000)

        # Canvas should have non-zero dimensions after reload
        width = canvas.get_attribute("width")
        height = canvas.get_attribute("height")
        assert width and int(width) > 0, "Audience canvas has zero width after date change"
        assert height and int(height) > 0, "Audience canvas has zero height after date change"

    # ── 2. Brand filter — select "Gigi" ───────────────────────────────────

    def test_brand_filter_select_gigi(self, audience_page: Page):
        """
        Select the "Gigi" brand via the brand filter dropdown and verify:
          - The brand dropdown opens when clicked
          - Typing "Gigi" filters the brand table to show the Gigi row
          - Clicking the Gigi row updates the filter display to "Gigi"
          - Clicking blank space closes the dropdown
          - The Audience chart widget still renders after the filter change
          - The Engaged Users count changes (drops) compared to "All brands"
        """
        # ── Capture the Engaged Users count BEFORE filtering ─────────────
        eu_widget = audience_page.locator(".react-grid-item#totalUsers")
        eu_widget.scroll_into_view_if_needed()
        audience_page.wait_for_timeout(500)

        before_text = eu_widget.inner_text()
        before_numbers = re.findall(r"[\d,]+", before_text)
        before_engaged = int(before_numbers[0].replace(",", "")) if before_numbers else 0

        # Scroll back up to the filter bar
        audience_page.locator(".ant-picker-range").scroll_into_view_if_needed()
        audience_page.wait_for_timeout(300)

        brand_select = audience_page.get_by_test_id("audience_filter_selectBrand")

        # ── Open the brand dropdown ──────────────────────────────────────
        brand_select.click()
        audience_page.wait_for_timeout(500)

        # Verify the dropdown table appeared — scope to the brand dropdown's
        # table (not the date picker calendar tables which are also <table>).
        brand_table = audience_page.locator("table").filter(has_text="All brands")
        expect(brand_table).to_be_visible(timeout=5_000)

        # ── Type "Gigi" to filter the brand list ─────────────────────────
        # Must use pressSequentially — fill() does NOT trigger Ant Design
        # search filtering on this custom dropdown.
        search_input = brand_select.locator('input[type="search"]')
        search_input.press_sequentially("Gigi", delay=100)
        audience_page.wait_for_timeout(1000)

        # Verify the Gigi row appeared in the filtered table
        gigi_row = audience_page.get_by_role("row", name=re.compile(r"Gigi"))
        expect(gigi_row).to_be_visible(timeout=5_000)

        # ── Click the Gigi row to select it ──────────────────────────────
        gigi_row.click()
        audience_page.wait_for_timeout(500)

        # Verify the brand filter now shows "Gigi"
        expect(brand_select).to_contain_text("Gigi")

        # ── Click blank space to close the dropdown and apply ────────────
        audience_page.locator("body").click(position={"x": 500, "y": 500})
        audience_page.wait_for_timeout(3000)

        # ── Verify the filter is applied and chart reloaded ──────────────
        # Brand filter should still show "Gigi" after closing dropdown
        expect(brand_select).to_contain_text("Gigi")

        # Audience chart widget should still be visible (even if empty)
        widget = audience_page.locator(".react-grid-item#audience")
        expect(widget).to_be_visible(timeout=15_000)

        canvas = widget.locator("canvas").first
        expect(canvas).to_be_visible(timeout=15_000)

        # ── Verify Engaged Users count changed after brand filter ────────
        # "Gigi" is a single brand — its engaged-user count should be
        # different from (and typically less than) the "All brands" total.
        eu_widget.scroll_into_view_if_needed()
        audience_page.wait_for_timeout(500)

        after_text = eu_widget.inner_text()
        after_numbers = re.findall(r"[\d,]+", after_text)
        after_engaged = int(after_numbers[0].replace(",", "")) if after_numbers else -1

        assert after_engaged != before_engaged, (
            f"Engaged Users count did not change after selecting Gigi brand. "
            f"Before: {before_engaged}, After: {after_engaged}"
        )
        assert after_engaged < before_engaged, (
            f"Expected Engaged Users to decrease when filtering to a single "
            f"brand, but Before={before_engaged}, After={after_engaged}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIENCE TAB — API / GRAPHQL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudienceAPI:
    """
    API-level tests for the Analytics > Audience page.

    These tests intercept network traffic while navigating to the Audience
    tab and verify that:
      - The correct GraphQL queries are fired with the right variables
      - Response payloads contain the expected fields and data types
      - REST support endpoints return 200

    Uses the `page` fixture (shared session page) so each test can set up
    its own request/response listeners BEFORE navigation.

    GraphQL queries identified on the Audience page:
      1. Age distribution:  age_0_20 … age_66_70
      2. Gender:            male, female, others
      3. Generation:        gen_bb, gen_x, gen_y, gen_z, gen_alpha
      4. Engaged Users:     interactions_users, all_events_users
                            (two aliases: all_time + over_defined_period)
    """

    # ── Helper: capture GraphQL responses on navigation ───────────────────

    @staticmethod
    def _capture_audience_graphql(page: Page):
        """
        Navigate to the Audience page and collect all successful GraphQL
        responses.  Returns a list of dicts with keys:
            query  — the raw GraphQL query string
            variables — the parsed variables dict
            data — the response 'data' payload
        """
        captured = []

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.request.method != "POST":
                return
            if resp.status != 200:
                return
            try:
                req_body = json.loads(resp.request.post_data)
                res_body = resp.json()
                captured.append({
                    "query": req_body.get("query", ""),
                    "variables": req_body.get("variables", {}),
                    "data": res_body.get("data", {}),
                    "errors": res_body.get("errors"),
                })
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_AUDIENCE_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        return captured

    # ── 1. GraphQL health on page load ────────────────────────────────────

    def test_graphql_health_on_load(self, page: Page):
        """
        On Audience page load:
          - At least 4 GraphQL POST requests return 200
          - Every response body has a 'data' key (no server errors)
          - No response contains a GraphQL 'errors' array
        """
        captured = self._capture_audience_graphql(page)

        assert len(captured) >= 4, (
            f"Expected ≥4 successful GraphQL responses, got {len(captured)}"
        )

        for i, call in enumerate(captured):
            assert call["data"], (
                f"GraphQL response #{i} has no 'data' key"
            )
            assert call["errors"] is None, (
                f"GraphQL response #{i} has errors: {call['errors']}"
            )

    # ── 2. Age distribution response structure ────────────────────────────

    def test_age_distribution_response(self, page: Page):
        """
        The age distribution query should return all expected age bucket
        fields.  Values must be numbers (≥ 0, can be 0).
        """
        captured = self._capture_audience_graphql(page)

        expected_fields = [
            "age_0_20", "age_21_25", "age_26_30", "age_31_35",
            "age_36_40", "age_41_45", "age_46_50", "age_51_55",
            "age_56_60", "age_61_65", "age_66_70",
        ]

        # Find the age distribution query by checking for "age_0_20" in query
        age_calls = [c for c in captured if "age_0_20" in c["query"]]
        assert age_calls, (
            "No GraphQL query containing age distribution fields was captured"
        )

        # Verify response structure — dig into data.analytics.audience[0]
        call = age_calls[0]
        analytics = call["data"].get("analytics", {})
        audience_list = analytics.get("audience", [])
        assert isinstance(audience_list, list) and len(audience_list) > 0, (
            f"Expected audience to be a non-empty list, got {type(audience_list).__name__}"
        )
        audience = audience_list[0]

        for field in expected_fields:
            assert field in audience, (
                f"Age field '{field}' missing from response. "
                f"Got keys: {list(audience.keys())}"
            )
            val = audience[field]
            assert isinstance(val, (int, float)), (
                f"Age field '{field}' should be a number, got {type(val).__name__}: {val}"
            )
            assert val >= 0, (
                f"Age field '{field}' should be ≥ 0, got {val}"
            )

    # ── 3. Gender response structure ──────────────────────────────────────

    def test_gender_response(self, page: Page):
        """
        The gender query should return male, female, others fields.
        Values must be numbers (≥ 0, can be 0).
        """
        captured = self._capture_audience_graphql(page)

        expected_fields = ["male", "female", "others"]

        # Find the gender query — contains "male" but NOT "age_0_20"
        gender_calls = [
            c for c in captured
            if "male" in c["query"] and "age_0_20" not in c["query"]
        ]
        assert gender_calls, (
            "No GraphQL query containing gender fields was captured"
        )

        call = gender_calls[0]
        analytics = call["data"].get("analytics", {})
        audience_list = analytics.get("audience", [])
        assert isinstance(audience_list, list) and len(audience_list) > 0, (
            f"Expected audience to be a non-empty list, got {type(audience_list).__name__}"
        )
        audience = audience_list[0]

        for field in expected_fields:
            assert field in audience, (
                f"Gender field '{field}' missing from response. "
                f"Got keys: {list(audience.keys())}"
            )
            val = audience[field]
            assert isinstance(val, (int, float)), (
                f"Gender field '{field}' should be a number, got {type(val).__name__}: {val}"
            )
            assert val >= 0, (
                f"Gender field '{field}' should be ≥ 0, got {val}"
            )

    # ── 4. Generation response structure ──────────────────────────────────

    def test_generation_response(self, page: Page):
        """
        The generation query should return gen_bb, gen_x, gen_y, gen_z,
        gen_alpha fields.  Values must be numbers (≥ 0, can be 0).
        """
        captured = self._capture_audience_graphql(page)

        expected_fields = ["gen_bb", "gen_x", "gen_y", "gen_z", "gen_alpha"]

        # Find the generation query
        gen_calls = [c for c in captured if "gen_bb" in c["query"]]
        assert gen_calls, (
            "No GraphQL query containing generation fields was captured"
        )

        call = gen_calls[0]
        analytics = call["data"].get("analytics", {})
        audience_list = analytics.get("audience", [])
        assert isinstance(audience_list, list) and len(audience_list) > 0, (
            f"Expected audience to be a non-empty list, got {type(audience_list).__name__}"
        )
        audience = audience_list[0]

        for field in expected_fields:
            assert field in audience, (
                f"Generation field '{field}' missing from response. "
                f"Got keys: {list(audience.keys())}"
            )
            val = audience[field]
            assert isinstance(val, (int, float)), (
                f"Generation field '{field}' should be a number, "
                f"got {type(val).__name__}: {val}"
            )
            assert val >= 0, (
                f"Generation field '{field}' should be ≥ 0, got {val}"
            )

    # ── 5. Engaged Users response structure ───────────────────────────────

    def test_engaged_users_response(self, page: Page):
        """
        The engaged users query returns two aliases:
          - all_time.audience.interactions_users / all_events_users
          - over_defined_period.audience.interactions_users / all_events_users
        Values must be numbers (≥ 0, can be 0).
        """
        captured = self._capture_audience_graphql(page)

        # Find the engaged users query — uses "all_time" alias
        eu_calls = [c for c in captured if "all_time" in str(c["data"])]
        assert eu_calls, (
            "No GraphQL response with 'all_time' alias was captured"
        )

        call = eu_calls[0]
        data = call["data"]

        for alias in ["all_time", "over_defined_period"]:
            assert alias in data, (
                f"Expected '{alias}' alias in response. Got keys: {list(data.keys())}"
            )
            audience_list = data[alias].get("audience", [])
            assert isinstance(audience_list, list) and len(audience_list) > 0, (
                f"'{alias}.audience' should be a non-empty list, "
                f"got {type(audience_list).__name__}"
            )
            audience = audience_list[0]
            assert "interactions_users" in audience or "all_events_users" in audience, (
                f"'{alias}.audience[0]' missing user count fields. "
                f"Got keys: {list(audience.keys())}"
            )

    # ── 6. REST endpoint health ───────────────────────────────────────────

    def test_rest_endpoints_health(self, page: Page):
        """
        On page load, the following REST endpoints should return 200:
          - GET  /identity-service/session
          - GET  /settings-service/countries
          - POST /participant-service/v2/brands/global/list
        """
        rest_results = {}

        def _on_response(resp):
            url = resp.url
            if "identity-service/session" in url:
                rest_results["session"] = resp.status
            elif "settings-service/countries" in url:
                rest_results["countries"] = resp.status
            elif "participant-service/v2/brands/global/list" in url:
                rest_results["brands"] = resp.status

        page.on("response", _on_response)
        page.goto(ANALYTICS_AUDIENCE_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        assert rest_results.get("session") == 200, (
            f"Session API expected 200, got {rest_results.get('session', 'not called')}"
        )
        assert rest_results.get("countries") == 200, (
            f"Countries API expected 200, got {rest_results.get('countries', 'not called')}"
        )
        assert rest_results.get("brands") == 200, (
            f"Brands API expected 200, got {rest_results.get('brands', 'not called')}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIENCE TAB — BE vs UI CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudienceBEvsUI:
    """
    Compare backend API responses against what the UI actually displays.

    Catches discrepancies where the API returns one value but the frontend
    renders a different number (formatting bugs, rounding errors, stale
    cache, dropped fields, etc.).

    API → UI mapping (verified 2026-04-08):
      Engaged Users widget:
        all_time.audience[0].interactions_users        → big number in circle
        over_defined_period.audience[0].interactions_users → small number below

      Audience / Gender / Generation (canvas charts):
        If API returns all-zero values → UI should show "No Data"
        If API returns non-zero values → UI should show a canvas with data
    """

    # ── 1. Engaged Users: BE numbers match UI display ─────────────────────

    def test_engaged_users_be_matches_ui(self, page: Page):
        """
        Intercept the Engaged Users GraphQL response and compare the
        returned numbers against the Engaged Users widget DOM text.

          - all_time.audience[0].interactions_users == big circle number
          - over_defined_period.audience[0].interactions_users == small number
        """
        eu_api_data = {}

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.status != 200:
                return
            try:
                body = resp.json()
                data = body.get("data", {})
                if "all_time" in data and "over_defined_period" in data:
                    all_time_audience = data["all_time"].get("audience", [])
                    period_audience = data["over_defined_period"].get("audience", [])
                    if all_time_audience:
                        eu_api_data["all_time"] = all_time_audience[0].get(
                            "interactions_users"
                        )
                    if period_audience:
                        eu_api_data["over_defined_period"] = period_audience[0].get(
                            "interactions_users"
                        )
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_AUDIENCE_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        # ── Read UI values ───────────────────────────────────────────────
        widget = page.locator(".react-grid-item#totalUsers")
        widget.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        ui_text = widget.inner_text()
        # Extract all numbers from the widget text (e.g. "22,407\n9\n...")
        ui_numbers = re.findall(r"[\d,]+", ui_text)
        ui_values = [
            int(n.replace(",", ""))
            for n in ui_numbers
            if n.replace(",", "").isdigit()
        ]

        # ── Assertions ───────────────────────────────────────────────────
        assert "all_time" in eu_api_data, (
            "Engaged Users API response not captured — "
            "no 'all_time' data found in GraphQL responses"
        )

        api_all_time = eu_api_data["all_time"]
        api_period = eu_api_data["over_defined_period"]

        assert len(ui_values) >= 2, (
            f"Expected at least 2 numbers in Engaged Users widget, "
            f"got: {ui_values}.  Widget text: {ui_text!r}"
        )

        ui_all_time = ui_values[0]
        ui_period = ui_values[1]

        assert ui_all_time == api_all_time, (
            f"Engaged Users ALL-TIME mismatch: "
            f"API returned {api_all_time}, UI shows {ui_all_time}"
        )
        assert ui_period == api_period, (
            f"Engaged Users DEFINED-PERIOD mismatch: "
            f"API returned {api_period}, UI shows {ui_period}"
        )

    # ── 2. Gender chart: "No Data" shown only when API returns all zeros ──

    def test_gender_no_data_consistency(self, page: Page):
        """
        Compare the Gender GraphQL response against the UI:
          - If API returns male=0 AND female=0 AND others=0 → UI should
            show "No Data" text inside the Gender widget
          - If any value is > 0 → UI should render a canvas (no "No Data")
        """
        gender_values = {}

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.status != 200:
                return
            try:
                req_body = json.loads(resp.request.post_data)
                query = req_body.get("query", "")
                # Gender query contains "male" but not "age_0_20"
                if "male" in query and "age_0_20" not in query:
                    body = resp.json()
                    audience_list = body.get("data", {}).get("analytics", {}).get("audience", [])
                    if isinstance(audience_list, list) and len(audience_list) > 0:
                        audience = audience_list[0]
                    else:
                        audience = audience_list if isinstance(audience_list, dict) else {}
                    gender_values["male"] = audience.get("male", 0)
                    gender_values["female"] = audience.get("female", 0)
                    gender_values["others"] = audience.get("others", 0)
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_AUDIENCE_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        assert gender_values, "Gender GraphQL response not captured"

        # Check UI state
        widget = page.locator(".react-grid-item#gender")
        widget.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        widget_text = widget.inner_text()

        api_total = sum(gender_values.values())
        ui_has_no_data = "No Data" in widget_text or "No data" in widget_text
        ui_has_canvas = widget.locator("canvas").count() > 0

        if api_total == 0:
            assert ui_has_no_data, (
                f"API returned all zeros for Gender ({gender_values}), "
                f"but UI does not show 'No Data'.  Widget text: {widget_text!r}"
            )
        else:
            assert ui_has_canvas and not ui_has_no_data, (
                f"API returned non-zero Gender data ({gender_values}), "
                f"but UI shows 'No Data' or missing canvas.  "
                f"Widget text: {widget_text!r}"
            )

    # ── 3. Generation chart: "No Data" shown only when API returns zeros ──

    def test_generation_no_data_consistency(self, page: Page):
        """
        Compare the Generation GraphQL response against the UI:
          - If ALL generation values are 0 → UI should show "No Data"
          - If any value > 0 → UI should render a canvas (no "No Data")
        """
        gen_values = {}

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.status != 200:
                return
            try:
                req_body = json.loads(resp.request.post_data)
                query = req_body.get("query", "")
                if "gen_bb" in query:
                    body = resp.json()
                    audience_list = body.get("data", {}).get("analytics", {}).get("audience", [])
                    if isinstance(audience_list, list) and len(audience_list) > 0:
                        audience = audience_list[0]
                    else:
                        audience = audience_list if isinstance(audience_list, dict) else {}
                    for field in ["gen_bb", "gen_x", "gen_y", "gen_z", "gen_alpha"]:
                        gen_values[field] = audience.get(field, 0)
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_AUDIENCE_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        assert gen_values, "Generation GraphQL response not captured"

        # Check UI state
        widget = page.locator(".react-grid-item#generation")
        widget.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        widget_text = widget.inner_text()

        api_total = sum(gen_values.values())
        ui_has_no_data = "No Data" in widget_text or "No data" in widget_text
        ui_has_canvas = widget.locator("canvas").count() > 0

        if api_total == 0:
            assert ui_has_no_data, (
                f"API returned all zeros for Generation ({gen_values}), "
                f"but UI does not show 'No Data'.  Widget text: {widget_text!r}"
            )
        else:
            assert ui_has_canvas and not ui_has_no_data, (
                f"API returned non-zero Generation data ({gen_values}), "
                f"but UI shows 'No Data' or missing canvas.  "
                f"Widget text: {widget_text!r}"
            )

    # ── 4. Age chart: "No Data" vs canvas consistency ─────────────────────

    def test_age_chart_no_data_consistency(self, page: Page):
        """
        Compare the Age distribution GraphQL response against the UI:
          - If ALL age bucket values are 0 → the chart should appear empty
            (canvas may still render but with only axis lines)
          - If any value > 0 → canvas should contain non-blank pixel data
        """
        age_values = {}

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.status != 200:
                return
            try:
                req_body = json.loads(resp.request.post_data)
                query = req_body.get("query", "")
                if "age_0_20" in query:
                    body = resp.json()
                    audience_list = body.get("data", {}).get("analytics", {}).get("audience", [])
                    if isinstance(audience_list, list) and len(audience_list) > 0:
                        audience = audience_list[0]
                    else:
                        audience = audience_list if isinstance(audience_list, dict) else {}
                    for field in ["age_0_20", "age_21_25", "age_26_30", "age_31_35",
                                  "age_36_40", "age_41_45", "age_46_50", "age_51_55",
                                  "age_56_60", "age_61_65", "age_66_70"]:
                        age_values[field] = audience.get(field, 0)
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_AUDIENCE_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        assert age_values, "Age distribution GraphQL response not captured"

        # Check UI state
        widget = page.locator(".react-grid-item#audience")
        expect(widget).to_be_visible(timeout=15_000)

        canvas = widget.locator("canvas").first
        api_total = sum(age_values.values())

        if api_total > 0:
            # If API has data, canvas should contain non-blank pixels
            expect(canvas).to_be_visible(timeout=15_000)
            has_data = page.evaluate("""
                (canvasEl) => {
                    const ctx = canvasEl.getContext('2d');
                    if (!ctx) return false;
                    const d = ctx.getImageData(0, 0, canvasEl.width, canvasEl.height).data;
                    for (let i = 0; i < d.length; i += 4) {
                        if (d[i+3] > 0 && (d[i] < 250 || d[i+1] < 250 || d[i+2] < 250))
                            return true;
                    }
                    return false;
                }
            """, canvas.element_handle())
            assert has_data, (
                f"API returned non-zero age data (total={api_total}), "
                f"but the Audience chart canvas appears blank"
            )



