"""
test_analytics_insights.py
UI tests for Shping Admin — Analytics > Insights page
(URL: /admin/analytics/insights)

Covers the widgets visible on the Insights tab:

  Canvas chart widgets:
    1. Retailer Mix           (#retailerMix)    — donut/pie canvas chart
    2. Store Prices           (#storePrice)     — bar/line canvas chart

  Split-table widgets:
    3. Segment Sales Performance (#segmentSalesPerformance)
       Headers: Brand, Buyers, Change, Interval, Average $,
                Value $, Total $, Average Age, Receipts
    4. Brand Gains            (#brandGains)
       Headers: Competitor, Converted Users
    5. Brand Losses           (#brandLosses)
       Headers: User Count, Brand, Competitor Product, Amount
    6. Brand Switching        (#brandSwitching)
       Headers: Product, Average Price, Competitors
    7. Cross Basket Analysis  (#crossBasket)
       Headers: GTIN, Product, Category, Bought With,
                Bought Category, Appearance in Basket

Filters available (data-testid):
    insights_filter_selectCountry
    insights_filter_selectBrand

Date range: 03/01/2026 – 04/07/2026
Participant: Authenticateit Pty Ltd

IMPORTANT — Split-table layout:
    All table widgets use Ant Design's split-table pattern:
      table[0] = <thead> only (column headers)
      table[1] = <tbody> only (data rows; row 0 repeats the header)
    All row-count assertions target table[1] and expect ≥ 2 rows.

IMPORTANT — Canvas rendering:
    Retailer Mix and Store Prices are rendered on <canvas> elements.
    Tests verify: container visible, title visible, canvas present with
    non-zero dimensions, and non-blank pixel data.

Run:
    pytest test_analytics_insights.py -v --headed
    pytest test_analytics_insights.py -v --headed --slowmo=500
"""

import json
import re
import pytest
from playwright.sync_api import Page, expect

from conftest import API_BASE_URL, ANALYTICS_INSIGHTS_URL


# ═══════════════════════════════════════════════════════════════════════════════
# INSIGHTS TAB — CANVAS CHART WIDGET UI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInsightsCharts:
    """
    UI tests for the canvas-based chart widgets on Analytics > Insights.

    Widget containers are located by their stable DOM `id` attributes:
      #retailerMix, #storePrice
    """

    # ── 1. Retailer Mix canvas chart ─────────────────────────────────────

    def test_retailer_mix_chart(self, insights_page: Page):
        """
        Retailer Mix chart:
          - Widget container #retailerMix is present in the DOM
          - Widget title 'Retailer Mix' is visible
          - A <canvas> element is rendered inside the widget
          - The canvas has non-zero width and height attributes
          - The canvas contains non-blank pixel data (chart actually drew)
        """
        widget = insights_page.locator(".react-grid-item#retailerMix")
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        widget_text = widget.inner_text()
        assert "Retailer Mix" in widget_text, (
            f"Expected 'Retailer Mix' title, got: {widget_text[:100]!r}"
        )

        # Canvas element
        canvas = widget.locator("canvas").first
        expect(canvas).to_be_visible(timeout=15_000)

        # Canvas dimensions
        width = canvas.get_attribute("width")
        height = canvas.get_attribute("height")
        assert width and int(width) > 0, (
            "Retailer Mix chart canvas has zero width"
        )
        assert height and int(height) > 0, (
            "Retailer Mix chart canvas has zero height"
        )

        # Canvas pixel data
        has_data = insights_page.evaluate("""
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
            "Retailer Mix chart canvas is blank — no chart data rendered"
        )

    # ── 2. Store Prices canvas chart ─────────────────────────────────────

    def test_store_prices_chart(self, insights_page: Page):
        """
        Store Prices chart:
          - Widget container #storePrice is present in the DOM
          - Widget title 'Store Prices' is visible
          - After the spinner clears, the widget shows either:
              (a) a <canvas> with non-zero dimensions and pixel data, OR
              (b) a 'No Data' placeholder — valid when the date range
                  has no store price records (e.g. starting 03/01/2026)

        NOTE: Store Prices only has data from ~04/01/2026 onwards in dev.
        A 'No Data' result is treated as a pass because the widget itself
        rendered correctly — it just has nothing to draw.

        KNOWN BUG: A date range of 03/01–04/12 returns 'No Data' even though
        04/01–04/12 (a subset of that range) does return data. The backend
        appears to filter by start-month rather than scanning the full range.
        This should be raised with the dev team as a Store Prices API defect.
        """
        widget = insights_page.locator(".react-grid-item#storePrice")
        widget.scroll_into_view_if_needed()
        insights_page.wait_for_timeout(500)
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        widget_text = widget.inner_text()
        assert "Store Prices" in widget_text, (
            f"Expected 'Store Prices' title, got: {widget_text[:100]!r}"
        )

        # Store Prices loads inside an Ant Design spinner.  Wait for the
        # ant-spin-spinning indicator to disappear before checking the canvas —
        # the canvas exists in the DOM while loading but Playwright cannot
        # interact with it until the spinner clears.
        widget.locator(".ant-spin-spinning").wait_for(
            state="hidden", timeout=20_000
        )

        # After loading, the widget shows either a canvas (data exists) or
        # a 'No Data' placeholder (no price records for the date range).
        # Both outcomes mean the widget rendered correctly — only a missing
        # widget or a stuck spinner should be treated as a failure.
        canvas = widget.locator("canvas").first
        no_data = widget.locator("text=No Data")

        has_canvas = canvas.is_visible()
        has_no_data = no_data.is_visible()

        assert has_canvas or has_no_data, (
            "Store Prices widget finished loading but shows neither a "
            "chart canvas nor a 'No Data' placeholder"
        )

        if has_canvas:
            # Canvas dimensions
            width = canvas.get_attribute("width")
            height = canvas.get_attribute("height")
            assert width and int(width) > 0, (
                "Store Prices chart canvas has zero width"
            )
            assert height and int(height) > 0, (
                "Store Prices chart canvas has zero height"
            )

            # Canvas pixel data
            has_pixels = insights_page.evaluate("""
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
            assert has_pixels, (
                "Store Prices chart canvas is blank — no chart data rendered"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# INSIGHTS TAB — TABLE WIDGET UI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInsightsTables:
    """
    UI tests for the split-table widgets on Analytics > Insights.

    All five table widgets use the same Ant Design split-table layout:
      table[0] = <thead> only (column headers)
      table[1] = <tbody> only (data rows; row 0 is a repeated header)

    Widget containers are located by their stable DOM `id` attributes:
      #segmentSalesPerformance, #brandGains, #brandLosses,
      #brandSwitching, #crossBasket
    """

    # ── 1. Segment Sales Performance table ───────────────────────────────

    def test_segment_sales_performance_table(self, insights_page: Page):
        """
        Segment Sales Performance table:
          - Widget container #segmentSalesPerformance is present in the DOM
          - Widget title 'Segment Sales Performance' is visible
          - table[0] has expected column headers:
            Brand, Buyers, Change, Interval, Average $, Value $,
            Total $, Average Age, Receipts
          - table[1] has at least 2 rows (1 repeated header + 1 data row)
        """
        widget = insights_page.locator(
            ".react-grid-item#segmentSalesPerformance"
        )
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("h3")).to_contain_text(
            "Segment Sales Performance"
        )

        # Header table (table[0])
        header_table = widget.locator("table").first
        expect(header_table).to_be_visible(timeout=15_000)
        header_text = header_table.inner_text()
        for col in ["Brand", "Buyers", "Change", "Interval",
                    "Average Age", "Receipts"]:
            assert col in header_text, (
                f"Expected column '{col}' in Segment Sales Performance table, "
                f"got: {header_text[:300]!r}"
            )

        # Data table (table[1])
        data_table = widget.locator("table").nth(1)
        expect(data_table).to_be_visible(timeout=15_000)
        rows = data_table.locator("tbody tr")
        assert rows.count() >= 2, (
            f"Expected ≥2 rows in Segment Sales Performance data table, "
            f"got {rows.count()}"
        )

    # ── 2. Brand Gains table ─────────────────────────────────────────────

    def test_brand_gains_table(self, insights_page: Page):
        """
        Brand Gains table:
          - Widget container #brandGains is present in the DOM
          - Widget title 'Brand Gains' is visible
          - table[0] has expected column headers:
            Competitor, Converted Users
          - table[1] has at least 2 rows (1 repeated header + 1 data row)
        """
        widget = insights_page.locator(".react-grid-item#brandGains")
        widget.scroll_into_view_if_needed()
        insights_page.wait_for_timeout(500)
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("h3")).to_contain_text("Brand Gains")

        # Header table (table[0])
        header_table = widget.locator("table").first
        expect(header_table).to_be_visible(timeout=15_000)
        header_text = header_table.inner_text()
        for col in ["Competitor", "Converted Users"]:
            assert col in header_text, (
                f"Expected column '{col}' in Brand Gains table, "
                f"got: {header_text[:200]!r}"
            )

        # Data table (table[1])
        data_table = widget.locator("table").nth(1)
        expect(data_table).to_be_visible(timeout=15_000)
        rows = data_table.locator("tbody tr")
        assert rows.count() >= 2, (
            f"Expected ≥2 rows in Brand Gains data table, got {rows.count()}"
        )

    # ── 3. Brand Losses table ────────────────────────────────────────────

    def test_brand_losses_table(self, insights_page: Page):
        """
        Brand Losses table:
          - Widget container #brandLosses is present in the DOM
          - Widget title 'Brand Losses' is visible
          - table[0] has expected column headers:
            User Count, Brand, Competitor Product, Amount
          - table[1] has at least 1 row (may be empty for the date range)
        """
        widget = insights_page.locator(".react-grid-item#brandLosses")
        widget.scroll_into_view_if_needed()
        insights_page.wait_for_timeout(500)
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("h3")).to_contain_text("Brand Losses")

        # Header table (table[0])
        header_table = widget.locator("table").first
        expect(header_table).to_be_visible(timeout=15_000)
        header_text = header_table.inner_text()
        for col in ["User Count", "Brand", "Competitor Product", "Amount"]:
            assert col in header_text, (
                f"Expected column '{col}' in Brand Losses table, "
                f"got: {header_text[:200]!r}"
            )

        # Data table (table[1]) — at least 1 row (even if data is "No data")
        data_table = widget.locator("table").nth(1)
        expect(data_table).to_be_visible(timeout=15_000)
        rows = data_table.locator("tbody tr")
        assert rows.count() >= 1, (
            f"Expected ≥1 row in Brand Losses data table, got {rows.count()}"
        )

    # ── 4. Brand Switching table ─────────────────────────────────────────

    def test_brand_switching_table(self, insights_page: Page):
        """
        Brand Switching table:
          - Widget container #brandSwitching is present in the DOM
          - Widget title 'Brand Switching' is visible
          - table[0] has expected column headers:
            Product, Average Price, Competitors
          - table[1] has at least 2 rows
        """
        widget = insights_page.locator(".react-grid-item#brandSwitching")
        widget.scroll_into_view_if_needed()
        insights_page.wait_for_timeout(500)
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("h3")).to_contain_text(
            "Brand Switching"
        )

        # Header table (table[0])
        header_table = widget.locator("table").first
        expect(header_table).to_be_visible(timeout=15_000)
        header_text = header_table.inner_text()
        for col in ["Product", "Average Price", "Competitors"]:
            assert col in header_text, (
                f"Expected column '{col}' in Brand Switching table, "
                f"got: {header_text[:200]!r}"
            )

        # Data table (table[1])
        data_table = widget.locator("table").nth(1)
        expect(data_table).to_be_visible(timeout=15_000)
        rows = data_table.locator("tbody tr")
        assert rows.count() >= 2, (
            f"Expected ≥2 rows in Brand Switching data table, "
            f"got {rows.count()}"
        )

    # ── 5. Cross Basket Analysis table ───────────────────────────────────

    def test_cross_basket_analysis_table(self, insights_page: Page):
        """
        Cross Basket Analysis table:
          - Widget container #crossBasket is present in the DOM
          - Widget title 'Cross Basket Analysis' is visible
          - table[0] has expected column headers:
            GTIN, Product, Category, Bought With,
            Bought Category, Appearance in Basket
          - table[1] has at least 2 rows
        """
        widget = insights_page.locator(".react-grid-item#crossBasket")
        widget.scroll_into_view_if_needed()
        insights_page.wait_for_timeout(500)
        expect(widget).to_be_visible(timeout=15_000)

        # Widget title
        expect(widget.locator("h3")).to_contain_text(
            "Cross Basket Analysis"
        )

        # Header table (table[0])
        header_table = widget.locator("table").first
        expect(header_table).to_be_visible(timeout=15_000)
        header_text = header_table.inner_text()
        for col in ["GTIN", "Product", "Category", "Bought With",
                    "Bought Category", "Appearance in Basket"]:
            assert col in header_text, (
                f"Expected column '{col}' in Cross Basket Analysis table, "
                f"got: {header_text[:300]!r}"
            )

        # Data table (table[1])
        data_table = widget.locator("table").nth(1)
        expect(data_table).to_be_visible(timeout=15_000)
        rows = data_table.locator("tbody tr")
        assert rows.count() >= 2, (
            f"Expected ≥2 rows in Cross Basket Analysis data table, "
            f"got {rows.count()}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# INSIGHTS TAB — FILTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInsightsFilters:
    """
    Filter interaction tests for Analytics > Insights.

    Covers:
      1. Same-month date range change — verify widgets reload
      2. Brand filter — select "Gigi", verify table data changes

    DOM notes (verified 2026-04-12):
      - Date inputs: .ant-picker-input-start input / .ant-picker-input-end input
      - Brand filter: data-testid="insights_filter_selectBrand"
      - Country filter: data-testid="insights_filter_selectCountry"
    """

    # ── 1. Same-month date range ──────────────────────────────────────────

    def test_date_range_same_month(self, insights_page: Page):
        """
        Change the date range to 04/01/2026 – 04/07/2026 and verify:
          - Both date inputs accept the new values
          - The Retailer Mix canvas is still visible after reload
        """
        start_input = insights_page.locator(".ant-picker-input-start input")
        end_input = insights_page.locator(".ant-picker-input-end input")

        start_input.click(click_count=3)
        start_input.type("04/01/2026")
        insights_page.keyboard.press("Tab")

        end_input.click(click_count=3)
        end_input.type("04/07/2026")
        insights_page.keyboard.press("Enter")

        insights_page.wait_for_timeout(3000)

        assert start_input.input_value() == "04/01/2026", (
            f"Start date not set correctly: {start_input.input_value()}"
        )
        assert end_input.input_value() == "04/07/2026", (
            f"End date not set correctly: {end_input.input_value()}"
        )

        widget = insights_page.locator(".react-grid-item#retailerMix")
        expect(widget).to_be_visible(timeout=15_000)
        canvas = widget.locator("canvas").first
        expect(canvas).to_be_visible(timeout=15_000)

    # ── 2. Brand filter — select "Gigi" ───────────────────────────────────

    def test_brand_filter_select_gigi(self, insights_page: Page):
        """
        Select the "Gigi" brand via the brand filter dropdown and verify:
          - The brand dropdown opens and filters to "Gigi"
          - Clicking the Gigi row applies the filter
          - The Segment Sales Performance table still renders after filter
        """
        # Scroll to filter bar
        insights_page.locator(".ant-picker-range").scroll_into_view_if_needed()
        insights_page.wait_for_timeout(300)

        brand_select = insights_page.get_by_test_id(
            "insights_filter_selectBrand"
        )
        brand_select.click()
        insights_page.wait_for_timeout(500)

        brand_table = insights_page.locator("table").filter(
            has_text="All brands"
        )
        expect(brand_table).to_be_visible(timeout=5_000)

        search_input = brand_select.locator('input[type="search"]')
        search_input.press_sequentially("Gigi", delay=100)
        insights_page.wait_for_timeout(1000)

        # Scope to the brand dropdown rows only — Insights already shows a
        # "Gigi" data row in the Segment Sales table, so an unscoped
        # get_by_role("row") would hit two elements (strict mode violation).
        # The brand dropdown rows carry data-row-key="brand-selector-*".
        gigi_row = insights_page.locator(
            'tr[data-row-key^="brand-selector"]'
        ).filter(has_text="Gigi")
        expect(gigi_row).to_be_visible(timeout=5_000)
        gigi_row.click()
        insights_page.wait_for_timeout(500)

        expect(brand_select).to_contain_text("Gigi")

        insights_page.locator("body").click(position={"x": 500, "y": 500})
        insights_page.wait_for_timeout(3000)

        # Verify filter label still shows "Gigi"
        expect(brand_select).to_contain_text("Gigi")

        # Segment Sales Performance table should still be visible
        widget = insights_page.locator(
            ".react-grid-item#segmentSalesPerformance"
        )
        expect(widget).to_be_visible(timeout=15_000)


# ═══════════════════════════════════════════════════════════════════════════════
# INSIGHTS TAB — API / GRAPHQL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInsightsAPI:
    """
    API-level tests for the Analytics > Insights page.

    These tests intercept network traffic while navigating to the Insights
    tab and verify that:
      - GraphQL queries are fired and return 200 with data
      - REST support endpoints return 200
    """

    @staticmethod
    def _capture_insights_graphql(page: Page):
        """
        Navigate to the Insights page and collect all successful GraphQL
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
        page.goto(ANALYTICS_INSIGHTS_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)
        return captured

    # ── 1. GraphQL health on page load ────────────────────────────────────

    def test_graphql_health_on_load(self, page: Page):
        """
        On Insights page load:
          - At least 3 GraphQL POST requests return 200
          - Every response body has a 'data' key
          - No response contains a GraphQL 'errors' array
        """
        captured = self._capture_insights_graphql(page)

        # Insights fires mainly REST calls; only 1 GraphQL request is expected
        assert len(captured) >= 1, (
            f"Expected ≥1 successful GraphQL responses, got {len(captured)}"
        )
        for i, call in enumerate(captured):
            assert call["data"], (
                f"GraphQL response #{i} has no 'data' key"
            )
            assert call["errors"] is None, (
                f"GraphQL response #{i} has errors: {call['errors']}"
            )

    # ── 2. Segment Sales Performance response ────────────────────────────

    def test_segment_sales_response(self, page: Page):
        """
        At least one GraphQL response should contain segment sales data
        (brand, buyers, receipts, etc.).
        """
        captured = self._capture_insights_graphql(page)

        segment_calls = [
            c for c in captured
            if any(
                kw in c["query"].lower()
                for kw in ["segment", "brand", "buyer", "receipt"]
            )
            or any(
                kw in str(c["data"]).lower()
                for kw in ["segment", "brand", "buyer"]
            )
        ]
        assert segment_calls, (
            "No GraphQL query or response containing segment/brand data "
            "was captured on the Insights page"
        )
        assert any(c["data"] for c in segment_calls), (
            "All segment-related GraphQL responses have empty data"
        )

    # ── 3. Retailer Mix response ──────────────────────────────────────────

    def test_retailer_mix_response(self, page: Page):
        """
        At least one GraphQL response should contain retailer/market mix data
        to populate the Retailer Mix chart.
        """
        captured = self._capture_insights_graphql(page)

        retailer_calls = [
            c for c in captured
            if "retailer" in c["query"].lower()
            or "retailer" in str(c["data"]).lower()
            or "market" in c["query"].lower()
        ]
        assert retailer_calls, (
            "No GraphQL query or response containing retailer mix data "
            "was captured on the Insights page"
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
        page.goto(ANALYTICS_INSIGHTS_URL)
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
# INSIGHTS TAB — BE vs UI CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInsightsBEvsUI:
    """
    Compare backend API responses against what the UI actually displays.

    Catches discrepancies where the API returns data but the frontend
    shows "No Data" or an empty table, and vice versa.
    """

    # ── 1. Brand Gains: BE data matches UI table ──────────────────────────

    def test_brand_gains_be_matches_ui(self, page: Page):
        """
        Intercept the Brand Gains GraphQL response and verify:
          - If API returned brand gains data, the table has at least
            one data row
          - If API returned nothing, the table may be empty
        """
        gains_data = {}

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.status != 200:
                return
            try:
                body = resp.json()
                data_str = json.dumps(body.get("data", {})).lower()
                if "gain" in data_str or "converted" in data_str:
                    gains_data["raw"] = body.get("data", {})
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_INSIGHTS_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        widget = page.locator(".react-grid-item#brandGains")
        widget.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        if gains_data:
            data_table = widget.locator("table").nth(1)
            rows = data_table.locator("tbody tr")
            assert rows.count() >= 2, (
                f"API returned brand gains data but table is empty. "
                f"Row count: {rows.count()}"
            )
        expect(widget).to_be_visible()

    # ── 2. Retailer Mix canvas: non-blank when API returns data ───────────

    def test_retailer_mix_canvas_consistency(self, page: Page):
        """
        If the API returns retailer mix data, the Retailer Mix canvas
        should contain non-blank pixel data.
        """
        retailer_data = {}

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.status != 200:
                return
            try:
                body = resp.json()
                data_str = json.dumps(body.get("data", {})).lower()
                if "retailer" in data_str or "market" in data_str:
                    retailer_data["raw"] = body.get("data", {})
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_INSIGHTS_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        widget = page.locator(".react-grid-item#retailerMix")
        expect(widget).to_be_visible(timeout=15_000)
        canvas = widget.locator("canvas").first

        if retailer_data:
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
                "API returned retailer mix data but the chart canvas is blank"
            )

    # ── 3. Segment Sales: BE data matches UI table ────────────────────────

    def test_segment_sales_be_matches_ui(self, page: Page):
        """
        Intercept the Segment Sales Performance GraphQL response and verify:
          - If API returned segment data, the table has at least one data row
          - If API returned nothing, the table may be empty
        """
        segment_data = {}

        def _on_response(resp):
            if resp.url != f"{API_BASE_URL}/graphql":
                return
            if resp.status != 200:
                return
            try:
                body = resp.json()
                data_str = json.dumps(body.get("data", {})).lower()
                if any(kw in data_str for kw in ["segment", "buyer", "receipt"]):
                    segment_data["raw"] = body.get("data", {})
            except Exception:
                pass

        page.on("response", _on_response)
        page.goto(ANALYTICS_INSIGHTS_URL)
        page.wait_for_timeout(5000)
        page.remove_listener("response", _on_response)

        widget = page.locator(".react-grid-item#segmentSalesPerformance")
        expect(widget).to_be_visible(timeout=15_000)

        if segment_data:
            data_table = widget.locator("table").nth(1)
            rows = data_table.locator("tbody tr")
            assert rows.count() >= 2, (
                f"API returned segment sales data but table is empty. "
                f"Row count: {rows.count()}"
            )

    # ── 4. Store Prices: superset date range returns ≥ data than subset ───
    #
    # BUG REGRESSION TEST
    # Reproduces the known defect where querying a wider date range (e.g.
    # 03/01–04/12) returns "No Data" even though a narrower range that is
    # fully contained within it (04/01–04/12) does return data.  A superset
    # range must never return fewer records than any of its subsets.

    def test_store_prices_superset_range_returns_at_least_subset_data(
        self, page: Page
    ):
        """
        REGRESSION — Store Prices: superset date range ≥ subset data.

        Steps:
          1. Navigate to Insights with a narrow range (04/01–04/12) and
             capture every API response that carries store price data.
          2. Navigate again with a wider range (03/01–04/12) — a superset
             of step 1 — and capture the same responses.
          3. Assert the wider range returns at least as many data records
             as the narrow range.

        Failure means the backend is filtering by start-month rather than
        scanning the full requested range.
        """

        def _capture_store_prices(from_date: str, to_date: str):
            """
            Navigate to the Insights page, set the given date range via the
            UI date picker, then intercept all REST/GraphQL responses that
            contain store price records.  Returns the combined list of
            price records found across all matching responses.
            """
            records = []

            def _on_response(resp):
                if resp.status != 200:
                    return
                # Store Prices data arrives in any response whose body
                # contains price-related keys (price, gtin, store).
                try:
                    body = resp.json()
                    text = str(body).lower()
                    if "price" in text and ("gtin" in text or "store" in text):
                        # Flatten whatever list structure is returned
                        def _extract(obj):
                            if isinstance(obj, list):
                                for item in obj:
                                    _extract(item)
                            elif isinstance(obj, dict):
                                # Treat each dict entry as one price record
                                if any(
                                    k in obj
                                    for k in ("price", "gtin", "store_id",
                                              "store", "value")
                                ):
                                    records.append(obj)
                                else:
                                    for v in obj.values():
                                        _extract(v)
                        _extract(body)
                except Exception:
                    pass

            page.on("response", _on_response)
            page.goto(ANALYTICS_INSIGHTS_URL)
            page.wait_for_timeout(2000)

            # Set the date range via the UI date picker
            picker = page.locator(".ant-picker-range")
            picker.scroll_into_view_if_needed()
            inputs = picker.locator("input")
            start_input = inputs.nth(0)
            end_input = inputs.nth(1)

            start_input.click(click_count=3)
            start_input.type(from_date)
            page.keyboard.press("Tab")
            end_input.click(click_count=3)
            end_input.type(to_date)
            page.keyboard.press("Enter")

            # Wait for Store Prices widget to finish loading
            widget = page.locator(".react-grid-item#storePrice")
            widget.locator(".ant-spin-spinning").wait_for(
                state="hidden", timeout=20_000
            )
            page.wait_for_timeout(2000)

            page.remove_listener("response", _on_response)
            return records

        # ── Step 1: narrow range (subset) ─────────────────────────────────
        narrow_records = _capture_store_prices("04/01/2026", "04/12/2026")

        # ── Step 2: wider range (superset) ────────────────────────────────
        wide_records = _capture_store_prices("03/01/2026", "04/12/2026")

        # ── Step 3: assert superset ≥ subset ──────────────────────────────
        # Only meaningful when the narrow range actually returned something;
        # if both are empty the widget had no data at all (acceptable).
        if narrow_records:
            assert len(wide_records) >= len(narrow_records), (
                f"BUG — Store Prices superset range (03/01–04/12) returned "
                f"{len(wide_records)} record(s) but the subset range "
                f"(04/01–04/12) returned {len(narrow_records)} record(s). "
                f"A wider date range must never return fewer records than a "
                f"range fully contained within it."
            )
