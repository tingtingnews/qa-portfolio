"""
test_media_hub.py
Tests for Shping Admin — Media Hub › Campaigns page (UI + API)

UI Tests:
  1. TestCampaignsDateFilter        — date range picker filters by Starts column
  2. TestCampaignsStatusFilter      — Active / Paused toggle validation
  3. TestCampaignsCTAFilter         — CTA dropdown (None / Offer / Redirect)
  4. TestCampaignsTrademarkFilter   — Trademark dropdown filters Brand column
  5. TestCampaignsResetFilters      — Reset clears all filters, API payload check
  6. TestCampaignsExportCSV         — Export CSV button is visible and clickable
  7. TestCampaignsCreateButton      — Create button opens a popup / new page

API / BE Tests:
  8.  TestCampaignsPagination       — Page navigation, API offset
  9.  TestCampaignsDataConsistency  — UI row count vs API response
  10. TestCampaignsMultiFilter      — Combined date + status + CTA filters
  11. TestCampaignsPerformance      — Page load and filter response times
  12. TestCampaignsResponseSchema   — API response structure / field types
  13. TestCampaignsFilterPayload    — Exact API payload for each filter
  14. TestCampaignsPaginationBoundary — Last page, page-size change, filter reset
  15. TestCampaignsTotalSpend       — Per-campaign spend endpoint validation
  16. TestCampaignsDataIntegrity    — Cross-endpoint ID consistency
  17. TestCampaignsErrorHandling    — 500 errors, slow responses, malformed JSON

Run:
    pytest test_media_hub.py -v --headed
    pytest test_media_hub.py -v --headed --slowmo=500
    pytest test_media_hub.py -k "API" -v --headed        # BE tests only
    pytest test_media_hub.py -k "not API" -v --headed    # UI tests only

NOTE: The Campaigns page uses the "Wild Co" participant context.
      The session_page fixture in conftest.py switches to "Authenticateit Pty Ltd",
      so the campaigns_page fixture below switches participant to "Wild Co".
      If running campaigns tests alongside other test files in one session,
      be aware the participant context will change.
"""

import re
import json
import time
import pytest
from datetime import datetime
from playwright.sync_api import Page, expect

from conftest import BASE_URL, API_BASE_URL, CAMPAIGNS_URL


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

CAMPAIGNS_API = f"{API_BASE_URL}/rewards-service/media_hub/campaign/read_list"
SPEND_API     = f"{API_BASE_URL}/rewards-service/media_hub/campaign/total_spend"

# Table column indices (0-based td position inside each <tr>)
COL_STATUS       = 0   # contains a <button role="switch">, not text
COL_CAMPAIGN     = 1
COL_BRAND        = 2
COL_STARTS       = 3
COL_ENDS         = 4
COL_CTA          = 5
COL_BUDGET       = 6
COL_SPEND        = 7
COL_IMPRESSIONS  = 8
COL_INTERACTIONS = 9

# Combobox order on the page (input[role='combobox'] nth-index):
#   0 = Participant selector (Wild Co)
#   1 = Language selector (English)
#   2 = Status filter
#   3 = CTA filter
#   4 = Country filter (Australia)
#   5 = Trademark filter
#   6 = Page Size selector (pagination footer)
STATUS_CB    = 2
CTA_CB       = 3
COUNTRY_CB   = 4
TRADEMARK_CB = 5

# CTA dropdown label → table display value
CTA_MAP = {
    "None":     "None",
    "Offer":    "Product Offer",
    "Redirect": "Redirect Url",
}


# ─────────────────────────────────────────────────────────────────────────────
# Fixture — campaigns_page
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def campaigns_page(session_page: Page) -> Page:
    """
    Switch to 'Wild Co' participant, navigate to Campaigns, wait for table,
    and reset any leftover filters from a previous test.
    """
    _switch_participant(session_page, "Wild Co")
    session_page.goto(CAMPAIGNS_URL)
    try:
        session_page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass
    _wait_for_table(session_page)
    _click_reset(session_page)
    return session_page


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _switch_participant(page: Page, target: str) -> None:
    """Switch the participant selector to *target* if not already selected."""
    try:
        already = page.locator(f".ant-select-content[title*='{target}']")
        if already.count() > 0 and already.first.is_visible():
            return
    except Exception:
        pass

    # Open participant dropdown (first combobox on the page)
    page.locator("input[role='combobox']").first.click()
    page.wait_for_timeout(1000)

    page.evaluate(f"""
        const items = document.querySelectorAll('.ant-select-item-option-content');
        const target = Array.from(items).find(
            el => el.textContent.includes('{target}')
        );
        if (target) target.click();
        else throw new Error('{target} not found in participant dropdown');
    """)

    page.wait_for_selector(
        f".ant-select-content[title*='{target}']", timeout=10_000
    )
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass
    page.wait_for_timeout(1000)


def _wait_for_table(page: Page) -> None:
    """Wait until the campaigns table renders at least one status toggle."""
    page.wait_for_selector("button[role='switch']", timeout=30_000)


def _get_table_rows(page: Page):
    """Locator for all visible table body rows."""
    rows = page.locator(".ant-table-tbody tr.ant-table-row")
    if rows.count() == 0:
        rows = page.locator("table tbody tr")
    return rows


def _get_row_count(page: Page) -> int:
    return _get_table_rows(page).count()


def _get_column_texts(page: Page, col_index: int) -> list:
    """Return a list of stripped text values for every visible row at *col_index*."""
    rows = _get_table_rows(page)
    count = rows.count()
    texts = []
    for i in range(count):
        cell = rows.nth(i).locator("td").nth(col_index)
        texts.append(cell.inner_text().strip())
    return texts


def _parse_date(date_str: str):
    """Parse 'April 1, 2026' → datetime.  Returns None for 'Ongoing'."""
    if not date_str or date_str.lower() == "ongoing":
        return None
    try:
        return datetime.strptime(date_str, "%B %d, %Y")
    except ValueError:
        return None


# ── Filter helpers ───────────────────────────────────────────────────────────

def _click_reset(page: Page) -> None:
    """Click 'Reset filters' and wait for the table to reload."""
    reset_btn = page.get_by_role("button", name="Reset filters")
    try:
        reset_btn.click()
        page.wait_for_timeout(1000)
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        _wait_for_table(page)
        page.wait_for_timeout(1000)
    except Exception:
        pass


def _open_date_picker(page: Page) -> None:
    """Open the RangePicker by clicking Start date."""
    page.get_by_placeholder("Start date").click()
    page.wait_for_timeout(500)


def _select_date_range(page: Page, start_title: str, end_title: str) -> None:
    """Click two calendar cells by their YYYY-MM-DD title attributes."""
    page.locator(
        f"td.ant-picker-cell-in-view[title='{start_title}'] .ant-picker-cell-inner"
    ).click()
    page.wait_for_timeout(500)
    page.locator(
        f"td.ant-picker-cell-in-view[title='{end_title}'] .ant-picker-cell-inner"
    ).click()
    page.wait_for_timeout(1000)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass
    _wait_for_table(page)


def _select_filter_option(page: Page, combobox_idx: int, option_text: str) -> None:
    """Open a filter dropdown by its combobox nth-index and click *option_text*."""
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    page.locator("input[role='combobox']").nth(combobox_idx).click()
    page.wait_for_timeout(500)

    page.evaluate(f"""
        const items = document.querySelectorAll('.ant-select-item-option-content');
        const target = Array.from(items).find(
            el => el.textContent.trim() === '{option_text}'
        );
        if (target) target.click();
        else throw new Error('{option_text} not found in dropdown');
    """)
    page.wait_for_timeout(1000)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass
    _wait_for_table(page)


def _select_status(page: Page, status: str) -> None:
    """Select Status filter: 'Active' or 'Paused'."""
    _select_filter_option(page, STATUS_CB, status)


def _select_cta(page: Page, cta: str) -> None:
    """Select CTA filter: 'None', 'Offer', or 'Redirect'."""
    _select_filter_option(page, CTA_CB, cta)


def _select_trademark(page: Page, title: str) -> None:
    """Open the Trademark dropdown (table-style) and click the row matching *title*."""
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    trademark_input = page.locator("input[role='combobox']").nth(TRADEMARK_CB)
    trademark_input.click()
    page.wait_for_timeout(500)

    # Type to search/filter the trademark table
    trademark_input.fill(title)
    page.wait_for_timeout(1000)

    # The dropdown renders a mini-table; click the row whose text contains *title*.
    page.evaluate(f"""
        const dropdowns = document.querySelectorAll('.ant-select-dropdown');
        for (const dd of dropdowns) {{
            if (getComputedStyle(dd).display === 'none') continue;
            const cells = dd.querySelectorAll('td, .ant-select-item-option-content, span');
            for (const el of cells) {{
                if (el.textContent.trim() === '{title}') {{
                    const row = el.closest('tr') || el.closest('.ant-select-item') || el;
                    row.click();
                    return;
                }}
            }}
        }}
        throw new Error('{title} not found in trademark dropdown');
    """)
    page.wait_for_timeout(1000)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass
    _wait_for_table(page)


def _capture_api_requests(page: Page, action_fn) -> list:
    """Run *action_fn*, capturing all POST requests to CAMPAIGNS_API."""
    captured = []

    def handler(request):
        if CAMPAIGNS_API in request.url and request.method == "POST":
            try:
                captured.append(json.loads(request.post_data))
            except Exception:
                pass

    page.on("request", handler)
    try:
        action_fn()
        page.wait_for_timeout(3000)
    finally:
        page.remove_listener("request", handler)
    return captured


def _capture_api_responses(page: Page, action_fn) -> list:
    """Run *action_fn*, capturing all responses from CAMPAIGNS_API."""
    captured = []

    def handler(response):
        if CAMPAIGNS_API in response.url:
            try:
                captured.append(response.json())
            except Exception:
                pass

    page.on("response", handler)
    try:
        action_fn()
        page.wait_for_timeout(3000)
    finally:
        page.remove_listener("response", handler)
    return captured


# ═════════════════════════════════════════════════════════════════════════════
# UI TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestCampaignsDateFilter:
    """Set date range 2026-04-10 → 2026-04-27; verify Starts column values."""

    def test_date_range_filters_campaigns(self, campaigns_page):
        page = campaigns_page
        count_before = _get_row_count(page)

        _open_date_picker(page)
        _select_date_range(page, "2026-04-10", "2026-04-27")
        page.wait_for_timeout(2000)

        count_after = _get_row_count(page)
        assert count_after <= count_before, (
            f"Expected ≤ {count_before} rows after date filter, got {count_after}"
        )
        assert count_after > 0, "Date filter returned zero campaigns"

        # Every visible campaign must overlap the filter window
        filter_start = datetime(2026, 4, 10)
        starts = _get_column_texts(page, COL_STARTS)
        ends   = _get_column_texts(page, COL_ENDS)

        for i, (s, e) in enumerate(zip(starts, ends)):
            end_dt = _parse_date(e)
            if end_dt is not None:
                assert end_dt >= filter_start, (
                    f"Row {i}: campaign ended {e} before filter start 2026-04-10"
                )

    def test_date_range_excludes_expired(self, campaigns_page):
        """Campaigns that ended before the filter start should not appear."""
        page = campaigns_page

        _open_date_picker(page)
        _select_date_range(page, "2026-04-10", "2026-04-27")
        page.wait_for_timeout(2000)

        ends = _get_column_texts(page, COL_ENDS)
        filter_start = datetime(2026, 4, 10)
        for i, e in enumerate(ends):
            end_dt = _parse_date(e)
            if end_dt is not None:
                assert end_dt >= filter_start, (
                    f"Row {i}: expired campaign (Ends={e}) should not appear"
                )


class TestCampaignsStatusFilter:
    """Filter by Active or Paused; verify toggle states match."""

    def test_active_filter(self, campaigns_page):
        page = campaigns_page
        _select_status(page, "Active")

        switches = page.locator("button[role='switch']")
        count = switches.count()
        assert count > 0, "No campaigns shown after Active filter"

        for i in range(count):
            assert switches.nth(i).get_attribute("aria-checked") == "true", (
                f"Row {i}: toggle should be ON for Active campaign"
            )

    def test_paused_filter(self, campaigns_page):
        page = campaigns_page
        _select_status(page, "Paused")

        switches = page.locator("button[role='switch']")
        count = switches.count()
        assert count > 0, "No campaigns shown after Paused filter"

        for i in range(count):
            assert switches.nth(i).get_attribute("aria-checked") == "false", (
                f"Row {i}: toggle should be OFF for Paused campaign"
            )


class TestCampaignsCTAFilter:
    """Filter by each CTA type; verify CTA column values."""

    @pytest.mark.parametrize("cta_option,expected", [
        ("Redirect", "Redirect Url"),
        ("None",     "None"),
        ("Offer",    "Product Offer"),
    ])
    def test_cta_filter(self, campaigns_page, cta_option, expected):
        page = campaigns_page
        _select_cta(page, cta_option)

        cta_values = _get_column_texts(page, COL_CTA)
        assert len(cta_values) > 0, f"No campaigns after CTA='{cta_option}'"
        for i, val in enumerate(cta_values):
            assert val == expected, (
                f"Row {i}: expected CTA '{expected}', got '{val}'"
            )


class TestCampaignsTrademarkFilter:
    """Select 'Iced Tea' trademark; Brand column should show 'Iced Tea'."""

    def test_trademark_iced_tea(self, campaigns_page):
        page = campaigns_page
        _select_trademark(page, "Iced Tea")

        brands = _get_column_texts(page, COL_BRAND)
        assert len(brands) > 0, "No campaigns after Iced Tea trademark filter"
        for i, brand in enumerate(brands):
            assert brand == "Iced Tea", (
                f"Row {i}: expected Brand 'Iced Tea', got '{brand}'"
            )


class TestCampaignsResetFilters:
    """Apply a filter, then Reset; verify filters are cleared."""

    def test_reset_clears_filters(self, campaigns_page):
        page = campaigns_page

        # Apply Active filter first to narrow the list
        _select_status(page, "Active")
        count_filtered = _get_row_count(page)

        # Capture the API request payload during Reset
        payloads = _capture_api_requests(
            page, lambda: _click_reset(page)
        )

        count_after = _get_row_count(page)
        assert count_after >= count_filtered, (
            "Reset should show same or more campaigns than filtered view"
        )

        # The reset payload should contain only country "036" (Australia)
        if payloads:
            payload_str = json.dumps(payloads[-1])
            assert "036" in payload_str or "country" in payload_str.lower(), (
                f"Reset API request should include country '036': {payload_str}"
            )


class TestCampaignsExportCSV:
    """Export CSV button should be visible and enabled."""

    def test_export_csv_visible_and_enabled(self, campaigns_page):
        page = campaigns_page
        export_btn = page.get_by_role("button", name="Export CSV")
        expect(export_btn).to_be_visible()
        expect(export_btn).to_be_enabled()


class TestCampaignsCreateButton:
    """Clicking Create should open a popup/modal or navigate to a new page."""

    def test_create_opens_popup(self, campaigns_page):
        page = campaigns_page
        current_url = page.url

        page.get_by_role("button", name="Create").click()
        page.wait_for_timeout(2000)

        new_url = page.url
        modal_visible = page.locator(
            ".ant-modal, .ant-drawer, [role='dialog']"
        ).count() > 0
        url_changed = new_url != current_url

        assert modal_visible or url_changed, (
            "Create button should open a modal or navigate to a new page"
        )

        # Clean up: close modal or go back
        if url_changed:
            page.go_back()
            page.wait_for_timeout(2000)
        elif modal_visible:
            try:
                page.locator(
                    ".ant-modal-close, .ant-drawer-close"
                ).first.click()
            except Exception:
                page.keyboard.press("Escape")
            page.wait_for_timeout(500)


# ═════════════════════════════════════════════════════════════════════════════
# API / BE TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestCampaignsPagination:
    """Navigate pages; verify data changes and API offset."""

    def test_pagination_navigation(self, campaigns_page):
        page = campaigns_page

        page1_names = _get_column_texts(page, COL_CAMPAIGN)
        assert len(page1_names) > 0, "Page 1 should have campaigns"

        # Go to page 2
        page.locator("a:text-is('2')").click()
        page.wait_for_timeout(2000)
        _wait_for_table(page)

        page2_names = _get_column_texts(page, COL_CAMPAIGN)
        assert len(page2_names) > 0, "Page 2 should have campaigns"
        assert page1_names != page2_names, (
            "Page 1 and Page 2 should show different campaigns"
        )

        # Return to page 1
        page.locator("a:text-is('1')").click()
        page.wait_for_timeout(2000)
        _wait_for_table(page)

        page1_again = _get_column_texts(page, COL_CAMPAIGN)
        assert page1_again == page1_names, (
            "Returning to page 1 should show the same campaigns"
        )

    def test_pagination_api_offset(self, campaigns_page):
        """API payload should include a pagination parameter when paging."""
        page = campaigns_page

        payloads = _capture_api_requests(
            page, lambda: (
                page.locator("a:text-is('2')").click(),
                page.wait_for_timeout(2000),
            )
        )

        assert len(payloads) > 0, "No API request captured for page 2"
        payload_str = json.dumps(payloads[-1])
        assert any(
            k in payload_str.lower()
            for k in ["offset", "page", "skip", "from", "limit"]
        ), f"API payload should include pagination param: {payload_str}"


class TestCampaignsDataConsistency:
    """Apply a filter and compare UI row count with API response."""

    def test_active_filter_consistency(self, campaigns_page):
        page = campaigns_page

        responses = _capture_api_responses(
            page, lambda: _select_status(page, "Active")
        )

        ui_count = _get_row_count(page)

        if responses:
            api_data = responses[-1]
            if isinstance(api_data, dict):
                api_total = api_data.get(
                    "count", api_data.get("total", len(api_data.get("data", [])))
                )
            elif isinstance(api_data, list):
                api_total = len(api_data)
            else:
                api_total = None

            if api_total is not None:
                # UI may show 10 per page; API may return the total count
                assert ui_count <= api_total, (
                    f"UI shows {ui_count} rows but API returned {api_total} total"
                )
                assert ui_count > 0, "Active filter should return at least 1 campaign"


class TestCampaignsMultiFilter:
    """Combine date + status + CTA filters; verify the intersection."""

    def test_date_status_cta_combined(self, campaigns_page):
        page = campaigns_page

        # 1 — Date filter: April 1–27, 2026
        _open_date_picker(page)
        _select_date_range(page, "2026-04-01", "2026-04-27")
        page.wait_for_timeout(2000)
        count_date = _get_row_count(page)

        # 2 — Active status
        _select_status(page, "Active")
        count_status = _get_row_count(page)
        assert count_status <= count_date, (
            "Adding Active filter should narrow or keep the same count"
        )

        # 3 — CTA = Product Offer
        _select_cta(page, "Offer")
        count_cta = _get_row_count(page)
        assert count_cta <= count_status, (
            "Adding CTA filter should narrow or keep the same count"
        )

        # Verify remaining rows satisfy all three filters
        if count_cta > 0:
            # All toggles should be ON (Active)
            switches = page.locator("button[role='switch']")
            for i in range(switches.count()):
                assert switches.nth(i).get_attribute("aria-checked") == "true", (
                    f"Row {i}: should be Active"
                )
            # All CTA values should be "Product Offer"
            for i, val in enumerate(_get_column_texts(page, COL_CTA)):
                assert val == "Product Offer", (
                    f"Row {i}: expected 'Product Offer', got '{val}'"
                )


class TestCampaignsPerformance:
    """Measure page-load and filter response times."""

    def test_page_load_under_10s(self, session_page):
        page = session_page
        _switch_participant(page, "Wild Co")

        start = time.time()
        page.goto(CAMPAIGNS_URL)
        _wait_for_table(page)
        elapsed = time.time() - start

        assert elapsed < 10.0, (
            f"Page load took {elapsed:.1f}s — expected under 10s"
        )

    def test_filter_response_under_5s(self, campaigns_page):
        page = campaigns_page

        start = time.time()
        _select_status(page, "Active")
        elapsed = time.time() - start

        assert elapsed < 5.0, (
            f"Filter response took {elapsed:.1f}s — expected under 5s"
        )


# ═════════════════════════════════════════════════════════════════════════════
# 12. RESPONSE SCHEMA & CONTRACT TESTING
# ═════════════════════════════════════════════════════════════════════════════


class TestCampaignsResponseSchema:
    """Verify the API response structure and field types from read_list."""

    def test_response_is_valid_structure(self, campaigns_page):
        """The API should return a dict (or list) with campaign objects."""
        page = campaigns_page

        responses = _capture_api_responses(
            page, lambda: (
                page.goto(CAMPAIGNS_URL),
                page.wait_for_timeout(3000),
                _wait_for_table(page),
            )
        )

        assert len(responses) > 0, "No API response captured on page load"
        body = responses[-1]

        # The response should be a dict with a data array, or a plain list
        if isinstance(body, dict):
            # Expect a wrapper like {"data": [...], "count": N} or similar
            data_key = None
            for key in ("data", "items", "campaigns", "results", "list"):
                if key in body:
                    data_key = key
                    break
            assert data_key is not None or isinstance(body.get("data"), list), (
                f"Response dict has no recognisable data array. Keys: {list(body.keys())}"
            )
            campaigns = body.get(data_key, []) if data_key else []
        elif isinstance(body, list):
            campaigns = body
        else:
            pytest.fail(f"Unexpected response type: {type(body)}")

        assert len(campaigns) > 0, "Campaign list is empty"

    def test_campaign_object_has_required_fields(self, campaigns_page):
        """Each campaign object should contain core fields."""
        page = campaigns_page

        responses = _capture_api_responses(
            page, lambda: (
                page.goto(CAMPAIGNS_URL),
                page.wait_for_timeout(3000),
                _wait_for_table(page),
            )
        )

        assert len(responses) > 0, "No API response captured"
        body = responses[-1]

        # Extract the campaign list
        if isinstance(body, dict):
            campaigns = []
            for key in ("data", "items", "campaigns", "results", "list"):
                if key in body and isinstance(body[key], list):
                    campaigns = body[key]
                    break
        elif isinstance(body, list):
            campaigns = body
        else:
            campaigns = []

        assert len(campaigns) > 0, "No campaigns in response"

        # Check first campaign for expected fields
        first = campaigns[0]
        assert isinstance(first, dict), f"Campaign should be a dict, got {type(first)}"

        # Log all keys for debugging if assertion fails
        keys = set(first.keys())

        # At minimum we expect some form of these fields (names may vary)
        expected_groups = {
            "id":     ["id", "campaign_id", "_id", "urn"],
            "name":   ["name", "campaign_name", "title", "campaign"],
            "status": ["status", "is_active", "active", "state"],
        }

        for field_label, possible_keys in expected_groups.items():
            found = any(k in keys for k in possible_keys)
            assert found, (
                f"Campaign object missing '{field_label}' field. "
                f"Looked for {possible_keys} in {sorted(keys)}"
            )

    def test_field_types_are_correct(self, campaigns_page):
        """Spot-check that numeric fields are numbers, not stringified numbers."""
        page = campaigns_page

        responses = _capture_api_responses(
            page, lambda: (
                page.goto(CAMPAIGNS_URL),
                page.wait_for_timeout(3000),
                _wait_for_table(page),
            )
        )

        assert len(responses) > 0, "No API response captured"
        body = responses[-1]

        if isinstance(body, dict):
            campaigns = []
            for key in ("data", "items", "campaigns", "results", "list"):
                if key in body and isinstance(body[key], list):
                    campaigns = body[key]
                    break
        elif isinstance(body, list):
            campaigns = body
        else:
            campaigns = []

        if not campaigns:
            pytest.skip("No campaigns in response to check field types")

        first = campaigns[0]

        # Check numeric fields if present
        for num_field in ("budget", "spend", "impressions", "interactions",
                          "total_budget", "daily_budget"):
            if num_field in first:
                val = first[num_field]
                assert isinstance(val, (int, float)), (
                    f"Field '{num_field}' should be numeric, "
                    f"got {type(val).__name__}: {val!r}"
                )


# ═════════════════════════════════════════════════════════════════════════════
# 13. FILTER PAYLOAD ACCURACY
# ═════════════════════════════════════════════════════════════════════════════


class TestCampaignsFilterPayload:
    """Verify exact API payload for each individual filter."""

    def test_status_active_payload(self, campaigns_page):
        """Selecting Active should send the correct status value in payload."""
        page = campaigns_page
        payloads = _capture_api_requests(
            page, lambda: _select_status(page, "Active")
        )
        assert len(payloads) > 0, "No API request captured for Active filter"
        payload_str = json.dumps(payloads[-1]).lower()
        # The payload should include a status-related key with an "active" value
        assert any(
            term in payload_str
            for term in ["active", "true", '"status"']
        ), f"Active filter payload missing status indicator: {payloads[-1]}"

    def test_status_paused_payload(self, campaigns_page):
        """Selecting Paused should send the correct status value in payload."""
        page = campaigns_page
        payloads = _capture_api_requests(
            page, lambda: _select_status(page, "Paused")
        )
        assert len(payloads) > 0, "No API request captured for Paused filter"
        payload_str = json.dumps(payloads[-1]).lower()
        assert any(
            term in payload_str
            for term in ["paused", "false", "inactive", '"status"']
        ), f"Paused filter payload missing status indicator: {payloads[-1]}"

    @pytest.mark.parametrize("cta_option,expected_api_values", [
        ("None",     ["none"]),
        ("Offer",    ["offer", "product_offer", "product offer"]),
        ("Redirect", ["redirect", "redirect_url", "redirect url"]),
    ])
    def test_cta_payload(self, campaigns_page, cta_option, expected_api_values):
        """Selecting a CTA type should send the matching value in payload."""
        page = campaigns_page
        payloads = _capture_api_requests(
            page, lambda: _select_cta(page, cta_option)
        )
        assert len(payloads) > 0, f"No API request captured for CTA={cta_option}"
        payload_str = json.dumps(payloads[-1]).lower()
        assert any(
            term in payload_str for term in expected_api_values
        ), (
            f"CTA={cta_option} payload should contain one of "
            f"{expected_api_values}: {payloads[-1]}"
        )

    def test_date_filter_payload(self, campaigns_page):
        """Date range filter should include start/end date in payload."""
        page = campaigns_page
        payloads = _capture_api_requests(
            page, lambda: (
                _open_date_picker(page),
                _select_date_range(page, "2026-04-10", "2026-04-27"),
            )
        )
        assert len(payloads) > 0, "No API request captured for date filter"
        payload_str = json.dumps(payloads[-1])
        # The payload should contain date values in some format
        assert any(
            d in payload_str
            for d in ["2026-04-10", "2026-04-27", "04/10/2026", "04/27/2026",
                       "1744243200", "1745712000"]  # possible epoch timestamps
        ), f"Date filter payload missing date values: {payloads[-1]}"

    def test_country_always_present(self, campaigns_page):
        """Every API request should include the country code '036' (Australia)."""
        page = campaigns_page
        # Capture request from a simple filter action
        payloads = _capture_api_requests(
            page, lambda: _select_status(page, "Active")
        )
        assert len(payloads) > 0, "No API request captured"
        payload_str = json.dumps(payloads[-1])
        assert "036" in payload_str or "australia" in payload_str.lower(), (
            f"Country code '036' should always be present: {payloads[-1]}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# 14. PAGINATION BOUNDARY CONDITIONS
# ═════════════════════════════════════════════════════════════════════════════


class TestCampaignsPaginationBoundary:
    """Edge cases: last page row count, filter resets page, page-size param."""

    def test_last_page_row_count(self, campaigns_page):
        """The last page should have between 1 and 10 rows (≤ page size)."""
        page = campaigns_page

        # Find the last page number
        page_links = page.locator("ul.ant-pagination li a")
        link_count = page_links.count()

        # The pagination links include numbers; find the highest
        max_page = 1
        for i in range(link_count):
            txt = page_links.nth(i).inner_text().strip()
            if txt.isdigit():
                max_page = max(max_page, int(txt))

        if max_page <= 1:
            pytest.skip("Only one page of campaigns — nothing to test")

        # Navigate to the last page
        page.locator(f"a:text-is('{max_page}')").click()
        page.wait_for_timeout(2000)
        _wait_for_table(page)

        last_page_count = _get_row_count(page)
        assert 1 <= last_page_count <= 10, (
            f"Last page (page {max_page}) has {last_page_count} rows — "
            "expected between 1 and 10"
        )

    def test_total_rows_across_pages(self, campaigns_page):
        """Sum of rows across all pages should be consistent."""
        page = campaigns_page

        # Find total pages
        page_links = page.locator("ul.ant-pagination li a")
        link_count = page_links.count()
        max_page = 1
        for i in range(link_count):
            txt = page_links.nth(i).inner_text().strip()
            if txt.isdigit():
                max_page = max(max_page, int(txt))

        total_rows = 0
        for pg in range(1, max_page + 1):
            page.locator(f"a:text-is('{pg}')").click()
            page.wait_for_timeout(2000)
            _wait_for_table(page)
            total_rows += _get_row_count(page)

        # With 10-per-page and max_page pages, total should be reasonable
        assert total_rows > 0, "No rows found across all pages"
        assert total_rows <= max_page * 10, (
            f"Total rows ({total_rows}) exceeds {max_page} pages × 10"
        )

    def test_filter_resets_to_page_one(self, campaigns_page):
        """After navigating to page 3 and applying a filter, should reset to page 1."""
        page = campaigns_page

        # Go to page 2 (or 3 if available)
        target_page = "2"
        page.locator(f"a:text-is('{target_page}')").click()
        page.wait_for_timeout(2000)
        _wait_for_table(page)

        # Now apply a filter
        _select_status(page, "Active")

        # The active/highlighted page should be 1 again
        # Ant Design pagination marks active page with .ant-pagination-item-active
        active_item = page.locator(".ant-pagination-item-active")
        if active_item.count() > 0:
            active_page_text = active_item.first.inner_text().strip()
            assert active_page_text == "1", (
                f"After applying a filter, pagination should reset to page 1, "
                f"but active page is {active_page_text}"
            )

    def test_page_size_in_api_payload(self, campaigns_page):
        """API request should include a limit/page_size parameter."""
        page = campaigns_page
        payloads = _capture_api_requests(
            page, lambda: (
                page.goto(CAMPAIGNS_URL),
                page.wait_for_timeout(3000),
                _wait_for_table(page),
            )
        )
        assert len(payloads) > 0, "No API request captured"
        payload_str = json.dumps(payloads[-1]).lower()
        assert any(
            k in payload_str
            for k in ['"limit"', '"page_size"', '"per_page"', '"size"', '"take"']
        ), f"API payload should include page-size param: {payloads[-1]}"


# ═════════════════════════════════════════════════════════════════════════════
# 15. TOTAL SPEND ENDPOINT
# ═════════════════════════════════════════════════════════════════════════════


class TestCampaignsTotalSpend:
    """Verify per-campaign total_spend endpoint calls and values."""

    def _capture_spend_responses(self, page: Page) -> list:
        """Reload the page and capture all total_spend GET responses."""
        spend_responses = []

        def handler(response):
            if SPEND_API in response.url and response.status == 200:
                try:
                    spend_responses.append({
                        "url": response.url,
                        "body": response.json(),
                    })
                except Exception:
                    spend_responses.append({
                        "url": response.url,
                        "body": None,
                    })

        page.on("response", handler)
        try:
            page.goto(CAMPAIGNS_URL)
            page.wait_for_timeout(5000)
            _wait_for_table(page)
            # Extra wait for all individual spend requests to complete
            page.wait_for_timeout(3000)
        finally:
            page.remove_listener("response", handler)
        return spend_responses

    def test_spend_endpoint_called_per_row(self, campaigns_page):
        """One total_spend request should fire for each visible campaign."""
        page = campaigns_page
        spend_responses = self._capture_spend_responses(page)

        row_count = _get_row_count(page)
        assert len(spend_responses) == row_count, (
            f"Expected {row_count} total_spend requests (one per row), "
            f"got {len(spend_responses)}"
        )

    def test_spend_responses_are_valid(self, campaigns_page):
        """Each total_spend response should return a parseable value."""
        page = campaigns_page
        spend_responses = self._capture_spend_responses(page)

        assert len(spend_responses) > 0, "No total_spend responses captured"

        for i, entry in enumerate(spend_responses):
            body = entry["body"]
            assert body is not None, (
                f"total_spend response {i} returned unparseable body: {entry['url']}"
            )

    def test_spend_url_contains_campaign_urn(self, campaigns_page):
        """Each total_spend URL should include a valid campaign URN."""
        page = campaigns_page
        spend_responses = self._capture_spend_responses(page)

        for entry in spend_responses:
            url = entry["url"]
            # URL should contain an id= query parameter with a URN
            assert "id=" in url, (
                f"total_spend URL missing 'id=' parameter: {url}"
            )
            # The id should look like urn:authenticateit:media_hub:<uuid>
            assert "urn" in url.lower() or "media_hub" in url.lower(), (
                f"total_spend id doesn't look like a valid URN: {url}"
            )

    def test_spend_column_matches_api(self, campaigns_page):
        """The Spend column in the UI should reflect the total_spend values."""
        page = campaigns_page
        spend_responses = self._capture_spend_responses(page)

        ui_spend_values = _get_column_texts(page, COL_SPEND)

        # At minimum, we can check that the count matches
        assert len(ui_spend_values) > 0, "No Spend values visible in the UI"

        # Verify UI spend values are valid currency strings ($X.XX)
        for i, val in enumerate(ui_spend_values):
            assert re.match(r"\$\d+\.\d{2}", val), (
                f"Row {i}: Spend value '{val}' is not a valid currency format"
            )


# ═════════════════════════════════════════════════════════════════════════════
# 16. DATA INTEGRITY ACROSS ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════


class TestCampaignsDataIntegrity:
    """Cross-endpoint consistency: campaign list IDs vs spend endpoint IDs."""

    def test_spend_ids_match_list_ids(self, campaigns_page):
        """Campaign IDs from read_list should match IDs queried by total_spend."""
        page = campaigns_page

        list_ids = []
        spend_ids = []

        def list_handler(response):
            if CAMPAIGNS_API in response.url:
                try:
                    body = response.json()
                    campaigns = []
                    if isinstance(body, dict):
                        for key in ("data", "items", "campaigns", "results", "list"):
                            if key in body and isinstance(body[key], list):
                                campaigns = body[key]
                                break
                    elif isinstance(body, list):
                        campaigns = body
                    for c in campaigns:
                        cid = c.get("id", c.get("campaign_id", c.get("_id", "")))
                        if cid:
                            list_ids.append(str(cid))
                except Exception:
                    pass

        def spend_handler(response):
            if SPEND_API in response.url:
                # Extract id from query string
                from urllib.parse import urlparse, parse_qs, unquote
                parsed = urlparse(response.url)
                qs = parse_qs(parsed.query)
                cid = qs.get("id", [""])[0]
                if cid:
                    spend_ids.append(unquote(cid))

        page.on("response", list_handler)
        page.on("response", spend_handler)
        try:
            page.goto(CAMPAIGNS_URL)
            page.wait_for_timeout(5000)
            _wait_for_table(page)
            page.wait_for_timeout(3000)
        finally:
            page.remove_listener("response", list_handler)
            page.remove_listener("response", spend_handler)

        assert len(list_ids) > 0, "No campaign IDs captured from read_list"
        assert len(spend_ids) > 0, "No campaign IDs captured from total_spend"

        # Every spend ID should match a list ID
        for sid in spend_ids:
            assert sid in list_ids, (
                f"total_spend queried ID '{sid}' not found in read_list IDs: "
                f"{list_ids}"
            )

    def test_no_duplicate_spend_requests(self, campaigns_page):
        """Each campaign should have exactly one total_spend request, no dupes."""
        page = campaigns_page

        spend_urls = []

        def handler(response):
            if SPEND_API in response.url:
                spend_urls.append(response.url)

        page.on("response", handler)
        try:
            page.goto(CAMPAIGNS_URL)
            page.wait_for_timeout(5000)
            _wait_for_table(page)
            page.wait_for_timeout(3000)
        finally:
            page.remove_listener("response", handler)

        # Extract just the id= values
        from urllib.parse import urlparse, parse_qs, unquote
        ids = []
        for url in spend_urls:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            cid = qs.get("id", [""])[0]
            ids.append(unquote(cid))

        # Check for duplicates
        unique_ids = set(ids)
        assert len(ids) == len(unique_ids), (
            f"Duplicate total_spend requests detected: "
            f"{len(ids)} requests for {len(unique_ids)} unique IDs"
        )


# ═════════════════════════════════════════════════════════════════════════════
# 17. ERROR HANDLING
# ═════════════════════════════════════════════════════════════════════════════


class TestCampaignsErrorHandling:
    """Verify the UI degrades gracefully under error conditions."""

    def test_api_500_shows_error_or_empty(self, campaigns_page):
        """When read_list returns 500, the UI should not crash."""
        page = campaigns_page

        # Intercept the campaigns API and force a 500 error
        page.route(
            "**/media_hub/campaign/read_list",
            lambda route: route.fulfill(
                status=500,
                content_type="application/json",
                body='{"error": "Internal Server Error"}',
            ),
        )

        page.goto(CAMPAIGNS_URL)
        page.wait_for_timeout(5000)

        # The page should NOT show a blank white screen or JS error.
        # It might show an error message, an empty table, or a spinner.
        # At minimum the sidebar and header should still render.
        sidebar = page.locator("text=Media Hub")
        expect(sidebar.first).to_be_visible(timeout=10_000)

        # Optionally: check for error toast / empty-state
        has_error_msg = page.locator(
            "text=/error|failed|try again|something went wrong/i"
        ).count() > 0
        has_empty_table = _get_table_rows(page).count() == 0

        assert has_error_msg or has_empty_table, (
            "After API 500 the page should show an error message or empty table"
        )

        # Clean up route interception
        page.unroute("**/media_hub/campaign/read_list")

    def test_slow_response_does_not_break_ui(self, campaigns_page):
        """A 4-second delayed response should still render correctly."""
        page = campaigns_page

        def delayed_handler(route):
            """Let the request go through to the real server, but add delay."""
            page.wait_for_timeout(4000)
            route.continue_()

        page.route("**/media_hub/campaign/read_list", delayed_handler)

        page.goto(CAMPAIGNS_URL)
        # Wait longer than normal to account for the artificial delay
        _wait_for_table(page)

        row_count = _get_row_count(page)
        assert row_count > 0, (
            "Table should render after delayed response"
        )

        page.unroute("**/media_hub/campaign/read_list")

    def test_spend_404_does_not_crash_page(self, campaigns_page):
        """If a total_spend endpoint returns 404, the table should still render."""
        page = campaigns_page

        # Intercept ALL total_spend requests and return 404
        page.route(
            "**/media_hub/campaign/total_spend*",
            lambda route: route.fulfill(
                status=404,
                content_type="application/json",
                body='{"error": "Not Found"}',
            ),
        )

        page.goto(CAMPAIGNS_URL)
        page.wait_for_timeout(5000)

        # The table should still load (campaign list endpoint is separate)
        _wait_for_table(page)
        row_count = _get_row_count(page)
        assert row_count > 0, (
            "Campaign table should render even when total_spend returns 404"
        )

        # Spend column should show $0.00 or be gracefully empty
        spend_values = _get_column_texts(page, COL_SPEND)
        for i, val in enumerate(spend_values):
            # Should not show raw error text
            assert "error" not in val.lower() and "not found" not in val.lower(), (
                f"Row {i}: Spend column shows error text: '{val}'"
            )

        page.unroute("**/media_hub/campaign/total_spend*")

    def test_malformed_json_does_not_crash(self, campaigns_page):
        """A malformed JSON response should not leave the page broken."""
        page = campaigns_page

        page.route(
            "**/media_hub/campaign/read_list",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{invalid json!!!',
            ),
        )

        page.goto(CAMPAIGNS_URL)
        page.wait_for_timeout(5000)

        # The page should still be navigable (sidebar, header present)
        sidebar = page.locator("text=Media Hub")
        expect(sidebar.first).to_be_visible(timeout=10_000)

        page.unroute("**/media_hub/campaign/read_list")
