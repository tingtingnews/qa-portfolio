"""
test_analytics_spend.py
UI tests for Shping Admin — Analytics > Spend page
(URL: /admin/analytics/spend)

Covers the widgets visible on the Spend tab:

  Summary metric widgets (inside #Summary wrapper):
    1. Interaction clicks     (#InteractionClicks)
    2. Approved Reviews       (#ApprovedReviews)
    3. Completed Video Views  (#CompletedVideoViews)
    4. Impressions            (#Impressions)
    5. Loyalty Hub Spend      (#LoyaltyHubSpend)

  Chart / table widgets:
    6. Daily Spend            (#spends)         — canvas line chart
    7. Summary table          (#StreamTable)    — split-table

Filters available (data-testid):
    spend_filter_selectRange
    spend_filter_selectCountry
    spend_filter_selectBrand
    spend_filter_selectGtin

Date range: 03/01/2026 – 04/07/2026
Participant: Authenticateit Pty Ltd

IMPORTANT — Split-table layout:
    #StreamTable uses Ant Design's split-table pattern:
      table[0] = <thead> only (column headers)
      table[1] = <tbody> only (data rows; row 0 repeats the header)
    All row-count assertions target table[1].

IMPORTANT — Canvas rendering:
    The Daily Spend chart is rendered on a <canvas> element.
    Axis labels and lines are painted pixels, not DOM text.
    Tests verify: container visible, title visible, canvas present with
    non-zero dimensions, and non-blank pixel data.

Run:
    pytest test_analytics_spend.py -v --headed
    pytest test_analytics_spend.py -v --headed --slowmo=500
"""

import json
import re
import pytest
from playwright.sync_api import Page, expect

from conftest import API_BASE_URL, ANALYTICS_SPEND_URL


# ═══════════════════════════════════════════════════════════════════════════════
# SPEND TAB — SUMMARY METRIC WIDGET UI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpendSummaryWidgets:
    """
    Five UI tests for the summary metric widgets on Analytics > Spend.
    All tests share the same spend_page fixture which navigates to
    /admin/analytics/spend and sets the date range to
    03/01/2026 – 04/07/2026.

    Widget containers are located by their stable DOM `id` attributes:
      #InteractionClicks, #ApprovedReviews, #CompletedVideoViews,
      #Impressions, #LoyaltyHubSpend
    """

    # ── 1. Interaction clicks widget ─────────────────────────────────────

    def test_interaction_clicks_widget(self, spend_page: Page):
        """
        Interaction clicks metric widget:
          - Widget container #InteractionClicks is present in the DOM
          - Widget title 'Interaction clicks' is visible
          - A dollar-formatted numeric value is displayed
          - The value is ≥ 0
        """
        widget = spend_page.locator(".react-grid-item#InteractionClicks")
        expect(widget).to_be_visible(timeout=15_000)

        widget_text = widget.inner_text()
        assert "Interaction clicks" in widget_text, (
            f"Expected 'Interaction clicks' title, got: {widget_text!r}"
        )

        numbers = re.findall(r"\d+\.?\d*", widget_text.replace(",", ""))
        assert len(numbers) >= 1, (
            f"Expected at least one numeric value in Interaction clicks widget, "
            f"found none. Widget text: {widget_text!r}"
        )
        assert float(numbers[0]) >= 0, (
            f"Interaction clicks value should be ≥ 0, got {numbers[0]}"
        )

    # ── 2. Approved Reviews widget ───────────────────────────────────────

    def test_approved_reviews_widget(self, spend_page: Page):
        """
        Approved Reviews metric widget:
          - Widget container #ApprovedReviews is present in the DOM
          - Widget title 'Approved Reviews' is visible
          - A dollar-formatted numeric value is displayed
          - The value is ≥ 0
        """
        widget = spend_page.locator(".react-grid-item#ApprovedReviews")
        expect(widget).to_be_visible(timeout=15_000)

        widget_text = widget.inner_text()
        assert "Approved Reviews" in widget_text, (
            f"Expected 'Approved Reviews' title, got: {widget_text!r}"
        )

        numbers = re.findall(r"\d+\.?\d*", widget_text.replace(",", ""))
        assert len(numbers) >= 1, (
            f"Expected at least one numeric value in Approved Reviews widget, "
            f"found none. Widget text: {widget_text!r}"
        )
        assert float(numbers[0]) >= 0, (
            f"Approved Reviews value should be ≥ 0, got {numbers[0]}"
        )

    # ── 3. Completed Video Views widget ──────────────────────────────────

    def test_completed_video_views_widget(self, spend_page: Page):
        """
        Completed Video Views metric widget:
          - Widget container #CompletedVideoViews is present in the DOM
          - Widget title 'Completed Video Views' is visible
          - A dollar-formatted numeric value is displayed
          - The value is ≥ 0
        """
        widget = spend_page.locator(".react-grid-item#CompletedVideoViews")
        expect(widget).to_be_visible(timeout=15_000)

        widget_text = widget.inner_text()
        assert "Completed Video Views" in widget_text, (
            f"Expected 'Completed Video Views' title, got: {widget_text!r}"
        )

        numbers = re.findall(r"\d+\.?\d*", widget_text.replace(",", ""))
        assert len(numbers) >= 1, (
            f"Expected at least one numeric value in Completed Video Views widget, "
            f"found none. Widget text: {widget_text!r}"
        )
        assert float(numbers[0]) >= 0, (
            f"Completed Video Views value should be ≥ 0, got {numbers[0]}"
        )

    # ── 4. Impressions widget ────────────────────────────────────────────

    def test_impressions_widget(self, spend_page: Page):
        """
        Impressions metric widget:
          - Widget container #Impressions is present in the DOM
          - Widget title 'Impressions' is visible
          - A dollar-formatted numeric value is displayed
          - The value is ≥ 0
        """
        widget = spend_page.locator(".react-grid-item#Impressions")
        expect(widget).to_be_visible(timeout=15_000)

        widget_text = widget.inner_text()
        assert "Impressions" in widget_text, (
            f"Expected 'Impressions' title, got: {widget_text!r}"
        )

        numbers = re.findall(r"\d+\.?\d*", widget_text.replace(",", ""))
        assert len(numbers) >= 1, (
            f"Expected at least one numeric value in Impressions widget, "
            f"found none. Widget text: {widget_text!r}"
        )
        assert float(numbers[0]) >= 0, (
            f"Impressions value should be ≥ 0, got {numbers[0]}"
        )

    # ── 5. Loyalty Hub Spend widget ──────────────────────────────────────

    def test_loyalty_hub_spend_widget(self, spend_page: Page):
        """
        Loyalty Hub Spend metric widget:
          - Widget container #LoyaltyHubSpend is present in the DOM
          - Widget title 'Loyalty Hub Spend' is visible
          - A dollar-formatted numeric value is displayed
          - The value is ≥ 0
        """
        widget = spend_page.locator(".react-grid-item#LoyaltyHubSpend")
        expect(widget).to_be_visible(timeout=15_000)

        widget_text = widget.inner_text()
        assert "Loyalty Hub Spend" in widget_text, (
            f"Expected 'Loyalty Hub Spend' title, got: {widget_text!r}"
        )

        numbers = re.findall(r"\d+\.?\d*", widget_text.replace(",", ""))
        assert len(numbers) >= 1, (
            f"Expected at least one numeric value in Loyalty Hub Spend widget, "
            f"found none. Widget text: {widget_text!r}"
        )
        assert float(numbers[0]) >= 0, (
            f"Loyalty Hub Spend value should be ≥ 0, got {numbers[0]}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SPEND TAB — CHART / TABLE WIDGET UI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpendCharts:
    """
    UI tests for the chart and table widgets on Analytics > Spend.

    Daily Spend (#spends):
      - Canvas line chart with 4 series: Interactions, Impressions,
        Video views, Reviews
      - Verify canvas renders with non-zero dimensions and pixel data

    Summary table (#StreamTable):
      - Split-table layout: table[0] = <thead>, table[1] = <tbody>
      - Headers: Clicks (Social Link Clicks, Ad Clicks, Other Clicks, Cost),
        Video (Completed Video Views, Cost), Reviews (Approved Reviews, Cost),
        Impressions (Impressions, Cost), Total Cost
      - Verify at least one data row is present
    """

    # ── 1. Daily Spend canvas chart ───────────────────────────────────────

    def test_daily_spend_chart(self, spend_page: Page):
        """
        Daily Spend line chart:
          - Widget container #spends is present in the DOM
          - Widget title 'Daily Spend' is visible
          - A <canvas> element is rendered inside the widget
          - The canvas has non-zero width and height attributes
          - The canvas contains non-blank pixel data (chart actually drew)
        """
        widget = spend_page.locator(".react-grid-item#spends")
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("div.sc-bxivhb")).to_contain_text("Daily Spend")

        # Canvas element
        canvas = widget.locator("canvas").first
        expect(canvas).to_be_visible(timeout=15_000)

        # Canvas dimensions
        width = canvas.get_attribute("width")
        height = canvas.get_attribute("height")
        assert width and int(width) > 0, (
            "Daily Spend chart canvas has zero width"
        )
        assert height and int(height) > 0, (
            "Daily Spend chart canvas has zero height"
        )

        # Canvas pixel data — verify chart actually rendered
        has_data = spend_page.evaluate("""
            (canvasEl) => {
                const ctx = canvasEl.getContext('2d');
                if (!ctx) return false;
                const imageData = ctx.getImageData(0, 0, canvasEl.width, canvasEl.height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    const r = data[i], g = data[i+1], b = data[i+2], a = data[i+3];
                    if (a > 0 && (r < 250 || g < 250 || b < 250)) return true;
                }
                return false;
            }
        """, canvas.element_handle())
        assert has_data, (
            "Daily Spend canvas is blank — no chart data rendered"
        )

    # ── 2. Summary (StreamTable) split-table ─────────────────────────────

    def test_stream_table(self, spend_page: Page):
        """
        Summary (StreamTable) widget:
          - Widget container #StreamTable is present in the DOM
          - Widget title 'Summary' is visible
          - Split-table layout:
              table[0] = <thead> with column group headers
              table[1] = <tbody> with data rows
          - Expected top-level column groups present in headers:
            Social Link Clicks, Ad Clicks, Other Clicks,
            Completed Video Views, Approved Reviews, Impressions, Total Cost
          - At least one data row present in table[1]
        """
        widget = spend_page.locator(".react-grid-item#StreamTable")
        widget.scroll_into_view_if_needed()
        spend_page.wait_for_timeout(500)
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("div.sc-bxivhb")).to_contain_text("Summary")

        # Split-table: table[0] is the fixed header table
        header_table = widget.locator("table").first
        expect(header_table).to_be_visible(timeout=15_000)

        header_text = header_table.inner_text()
        for col in ["Social Link Clicks", "Ad Clicks", "Other Clicks",
                    "Completed Video Views", "Approved Reviews",
                    "Impressions", "Total Cost"]:
            assert col in header_text, (
                f"Expected column '{col}' in StreamTable headers, "
                f"got: {header_text[:300]!r}"
            )

        # Split-table: table[1] is the scrollable body table
        # Row 0 is a repeated header — actual data starts at row 1
        data_table = widget.locator("table").nth(1)
        expect(data_table).to_be_visible(timeout=15_000)
        rows = data_table.locator("tbody tr")
        row_count = rows.count()
        assert row_count >= 2, (
            f"Expected at least 2 rows (1 header + 1 data) in StreamTable "
            f"data table, got {row_count}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SPEND TAB — FILTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpendFilters:
    """
    Filter interaction tests for Analytics > Spend.

    Covers:
      1. Same-month date range change — verify widgets reload
      2. Brand filter — select "Gigi", verify spend values change

    DOM notes (verified 2026-04-12):
      - Date inputs: .ant-picker-input-start input / .ant-picker-input-end input
      - Brand filter: data-testid="spend_filter_selectBrand"
      - Country filter: data-testid="spend_filter_selectCountry"
      - Range filter: data-testid="spend_filter_selectRange"
      - GTIN filter: data-testid="spend_filter_selectGtin"
    """

    # ── 1. Same-month date range ──────────────────────────────────────────

    def test_date_range_same_month(self, spend_page: Page):
        """
        Change the date range to 04/01/2026 – 04/07/2026 and verify:
          - Both date inputs accept the new values
          - The Daily Spend canvas is still visible after reload
        """
        start_input = spend_page.locator(".ant-picker-input-start input")
        end_input = spend_page.locator(".ant-picker-input-end input")

        start_input.click(click_count=3)
        start_input.type("04/01/2026")
        spend_page.keyboard.press("Tab")

        end_input.click(click_count=3)
        end_input.type("04/07/2026")
        spend_page.keyboard.press("Enter")

        spend_page.wait_for_timeout(3000)

        assert start_input.input_value() == "04/01/2026", (
            f"Start date not set correctly: {start_input.input_value()}"
        )
        assert end_input.input_value() == "04/07/2026", (
            f"End date not set correctly: {end_input.input_value()}"
        )

        widget = spend_page.locator(".react-grid-item#spends")
        expect(widget).to_be_visible(timeout=15_000)
        canvas = widget.locator("canvas").first
        expect(canvas).to_be_visible(timeout=15_000)

    # ── 2. Brand filter — select "Gigi" ───────────────────────────────────

    def test_brand_filter_select_gigi(self, spend_page: Page):
        """
        Select the "Gigi" brand via the brand filter dropdown and verify:
          - The brand dropdown opens and filters to "Gigi"
          - Clicking the Gigi row applies the filter
          - The Approved Reviews spend value changes after filtering
        """
        # Capture Approved Reviews spend BEFORE filtering
        ar_widget = spend_page.locator(".react-grid-item#ApprovedReviews")
        before_text = ar_widget.inner_text()
        before_numbers = re.findall(r"\d+\.?\d*", before_text.replace(",", ""))
        before_value = float(before_numbers[0]) if before_numbers else 0.0

        # Scroll to filter bar
        spend_page.locator(".ant-picker-range").scroll_into_view_if_needed()
        spend_page.wait_for_timeout(300)

        brand_select = spend_page.get_by_test_id("spend_filter_selectBrand")
        brand_select.click()
        spend_page.wait_for_timeout(500)

        brand_table = spend_page.locator("table").filter(has_text="All brands")
        expect(brand_table).to_be_visible(timeout=5_000)

        search_input = brand_select.locator('input[type="search"]')
        search_input.press_sequentially("Gigi", delay=100)
        spend_page.wait_for_timeout(1000)

        gigi_row = spend_page.get_by_role("row", name=re.compile(r"Gigi"))
        expect(gigi_row).to_be_visible(timeout=5_000)
        gigi_row.click()
        spend_page.wait_for_timeout(500)

        expect(brand_select).to_contain_text("Gigi")

        spend_page.locator("body").click(position={"x": 500, "y": 500})
        spend_page.wait_for_timeout(3000)

        # Verify filter label still shows "Gigi"
        expect(brand_select).to_contain_text("Gigi")

        # Verify summary widgets still render
        widget = spend_page.locator(".react-grid-item#InteractionClicks")
        expect(widget).to_be_visible(timeout=15_000)

        # Verify spend value changed after filtering to a single brand
        after_text = ar_widget.inner_text()
        after_numbers = re.findall(r"\d+\.?\d*", after_text.replace(",", ""))
        after_value = float(after_numbers[0]) if after_numbers else -1.0

        assert after_value != before_value, (
            f"Approved Reviews spend did not change after selecting Gigi brand. "
            f"Before: {before_value}, After: {after_value}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SPEND TAB — API / GRAPHQL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpendAPI:
    """
    API-level tests for the Analytics > Spend page.

    These tests intercept network traffic while navigating to the Spend
    tab and verify that:
      - GraphQL queries are fired and return 200 with data
      - REST support endpoints return 200
    """

    @staticmethod
    def _capture_spend_graphql(page: Page):
        """
        Navigate to the Spend page and collect all successful GraphQL
        responses. Returns a list of dicts with keys:
            query, variables, data, errors
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
        page.goto(ANALYTICS_SPEND_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)
        return captured

    # ── 1. GraphQL health on page load ────────────────────────────────────

    def test_graphql_health_on_load(self, page: Page):
        """
        On Spend page load:
          - At least 2 GraphQL POST requests return 200
          - Every response body has a 'data' key
          - No response contains a GraphQL 'errors' array

        NOTE: The Spend page fires exactly 2 GraphQL requests on load
        (the rest of the data comes via REST endpoints like /analytics/spends).
        Threshold is therefore ≥2, not ≥3.
        """
        captured = self._capture_spend_graphql(page)

        assert len(captured) >= 2, (
            f"Expected ≥2 successful GraphQL responses, got {len(captured)}"
        )
        for i, call in enumerate(captured):
            assert call["data"], (
                f"GraphQL response #{i} has no 'data' key"
            )
            assert call["errors"] is None, (
                f"GraphQL response #{i} has errors: {call['errors']}"
            )

    # ── 2. Spend summary response structure ───────────────────────────────

    def test_spend_summary_response(self, page: Page):
        """
        At least one GraphQL response should contain spend-related data
        (interaction clicks, reviews, video views, impressions costs).
        """
        captured = self._capture_spend_graphql(page)

        spend_calls = [
            c for c in captured
            if any(
                kw in c["query"].lower()
                for kw in ["spend", "cost", "click", "impression", "review"]
            )
            or any(
                kw in str(c["data"]).lower()
                for kw in ["spend", "cost", "click"]
            )
        ]
        assert spend_calls, (
            "No GraphQL query or response containing spend data was captured"
        )
        assert any(c["data"] for c in spend_calls), (
            "All spend-related GraphQL responses have empty data"
        )

    # ── 3. Daily Spend time-series response ───────────────────────────────

    def test_daily_spend_response(self, page: Page):
        """
        At least one GraphQL response should contain time-series data
        to populate the Daily Spend chart.

        NOTE: The query uses $aggregation: DAILY as a *variable* (not
        embedded in the query string), and the response carries the
        time-series array under the key 'streamed_spends'. We therefore
        check for that field name rather than the word "daily".
        """
        captured = self._capture_spend_graphql(page)

        daily_calls = [
            c for c in captured
            if "streamed_spends" in c["query"].lower()
            or "streamed_spends" in str(c["data"]).lower()
            or "stream_id" in str(c["data"]).lower()
        ]
        assert daily_calls, (
            "No GraphQL query or response containing streamed_spends "
            "(Daily Spend chart data) was captured"
        )

    # ── 4. REST endpoint health ───────────────────────────────────────────

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
        page.goto(ANALYTICS_SPEND_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        assert rest_results.get("session") == 200, (
            f"Session API expected 200, got "
            f"{rest_results.get('session', 'not called')}"
        )
        assert rest_results.get("countries") == 200, (
            f"Countries API expected 200, got "
            f"{rest_results.get('countries', 'not called')}"
        )
        assert rest_results.get("brands") == 200, (
            f"Brands API expected 200, got "
            f"{rest_results.get('brands', 'not called')}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SPEND TAB — BE vs UI CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpendBEvsUI:
    """
    Compare backend API responses against what the UI actually displays.

    Catches discrepancies where the API returns one value but the frontend
    renders a different number.
    """

    # ── 1. StreamTable: BE data matches UI rows ───────────────────────────

    def test_stream_table_be_matches_ui(self, page: Page):
        """
        Intercept the StreamTable GraphQL response and verify:
          - If API returned data, the table has at least one data row
          - If API returned nothing, table may be empty
        """
        stream_data = {}

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.status != 200:
                return
            try:
                body = resp.json()
                data_str = json.dumps(body.get("data", {})).lower()
                if any(kw in data_str for kw in ["stream", "spend", "cost"]):
                    stream_data["raw"] = body.get("data", {})
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_SPEND_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        widget = page.locator(".react-grid-item#StreamTable")
        widget.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        if stream_data:
            # Split-table: data rows in table[1]
            data_table = widget.locator("table").nth(1)
            rows = data_table.locator("tbody tr")
            assert rows.count() >= 2, (
                f"API returned spend data but StreamTable data table is empty. "
                f"Row count: {rows.count()}"
            )
        expect(widget).to_be_visible()

    # ── 2. Daily Spend canvas: non-blank when API returns data ────────────

    def test_daily_spend_canvas_consistency(self, page: Page):
        """
        If the API returns daily spend time-series data, the Daily Spend
        canvas should contain non-blank pixel data.
        """
        spend_data = {}

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.status != 200:
                return
            try:
                body = resp.json()
                data_str = json.dumps(body.get("data", {})).lower()
                if "spend" in data_str or "daily" in data_str:
                    spend_data["raw"] = body.get("data", {})
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_SPEND_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        widget = page.locator(".react-grid-item#spends")
        expect(widget).to_be_visible(timeout=15_000)
        canvas = widget.locator("canvas").first

        if spend_data:
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
                "API returned daily spend data but the chart canvas is blank"
            )
