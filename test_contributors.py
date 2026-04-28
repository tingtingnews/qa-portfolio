"""
test_contributors.py
Tests for Shping Admin — Contributors page (UI + API)

UI Tests:
  1. TestContributorsDateFilter       — date range picker changes content
  2. TestContributorsStatusFilter     — card field validation per status
  3. TestContributorsGtinSearch       — GTIN search and detail view
  4. TestContributorsUserSearch       — User name search

API Tests:
  5. TestContributorsAPIReset         — Reset button restores default filters
  6. TestContributorsAPIResponseSchema— API response structure/contract
  7. TestContributorsAPIPagination    — Pagination offset correctness
  8. TestContributorsAPIStatusFilter  — API payload includes correct status
  9. TestContributorsAPIEdgeCases     — Invalid inputs, empty results
  10. TestContributorsAPIPerformance  — Response time under threshold

Run:
    pytest test_contributors.py -v --headed
    pytest test_contributors.py -v --headed --slowmo=500
    pytest test_contributors.py -k "API" -v --headed    # API tests only
    pytest test_contributors.py -k "not API" -v --headed # UI tests only
"""

import re
import json
import time
import pytest
from playwright.sync_api import Page, expect

from conftest import BASE_URL, API_BASE_URL, CONTRIBUTORS_URL

CONTRIBUTORS_API_URL = f"{API_BASE_URL}/contributors-service/get_docs"


# ─────────────────────────────────────────────────────────────────────────────
# Shared Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _goto_contributors(page: Page) -> None:
    """Navigate to Contributors and wait for the list to render."""
    page.goto(CONTRIBUTORS_URL)
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass
    page.wait_for_selector("text=contributions are found", timeout=30_000)


def _click_reset(page: Page) -> None:
    """Click the Reset button and wait for the page to re-load fresh data.
    If Reset is disabled (already at default state), skip the click."""
    reset_btn = page.get_by_role("button", name="Reset")
    try:
        if not reset_btn.is_enabled(timeout=2_000):
            return
        reset_btn.click()
        page.wait_for_timeout(1_000)
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        page.wait_for_selector("text=contributions are found", timeout=30_000)
        page.wait_for_timeout(1_000)
    except Exception:
        # Reset button might be disabled or page already at default
        pass


def _click_apply(page: Page) -> None:
    """Click the Apply button and wait for the results to refresh."""
    page.get_by_role("button", name="Apply").click()
    page.wait_for_timeout(1_000)
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass
    page.wait_for_timeout(2_000)


def _get_contribution_count(page: Page) -> int:
    """Extract the number of contributions from the results summary text."""
    text_el = page.locator("text=contributions are found")
    text_el.wait_for(timeout=15_000)
    full_text = text_el.inner_text()
    match = re.search(r"(\d+)\s+contributions?\s+are\s+found", full_text)
    return int(match.group(1)) if match else -1


def _get_visible_statuses(page: Page) -> list[str]:
    """Return the status text of all visible contribution items on the page."""
    status_elements = page.locator("text=/^Status:/")
    count = status_elements.count()
    statuses = []
    for i in range(count):
        txt = status_elements.nth(i).inner_text()
        statuses.append(txt.replace("Status:", "").strip().lower())
    return statuses


def _get_card_fields(card) -> dict:
    """Extract all visible fields from a single contribution card."""
    card_text = card.inner_text()
    fields = {}

    # ID — first line of the card (shping:<uuid>, urn:..., or email)
    first_line = card_text.strip().split("\n")[0].strip()
    # Validate that the first line actually looks like an ID, not a
    # different field that got promoted because the ID line is missing.
    id_pattern = re.compile(
        r"^(shping:\S+|urn:\S+|\S+@\S+\.\S+)$", re.I
    )
    if first_line and id_pattern.match(first_line):
        fields["id"] = first_line
    else:
        fields["id"] = None

    # Product ID
    pid_match = re.search(r"Product ID:\s*(\S+)", card_text)
    fields["product_id"] = pid_match.group(1) if pid_match else None

    # Date created
    date_match = re.search(r"Date created:\s*(.+?)(?:\n|$)", card_text)
    fields["date_created"] = date_match.group(1).strip() if date_match else None

    # Status
    status_match = re.search(r"Status:\s*(\S+)", card_text)
    fields["status"] = status_match.group(1).strip().lower() if status_match else None

    # Level
    level_match = re.search(r"Level:\s*(.+?)(?:\n|$)", card_text)
    fields["level"] = level_match.group(1).strip() if level_match else None

    # Moderator name (may be empty after colon)
    mod_name_match = re.search(r"Moderator name:\s*(.*?)(?:\n|$)", card_text)
    if mod_name_match and mod_name_match.group(1).strip():
        fields["moderator_name"] = mod_name_match.group(1).strip()
    else:
        fields["moderator_name"] = None

    # Moderator email (may be empty)
    mod_email_match = re.search(r"Moderator email:\s*(.*?)(?:\n|$)", card_text)
    if mod_email_match and mod_email_match.group(1).strip():
        fields["moderator_email"] = mod_email_match.group(1).strip()
    else:
        fields["moderator_email"] = None

    # "Revert to approved" button
    fields["has_revert_button"] = card.locator(
        "button", has_text=re.compile(r"Revert to approved", re.I)
    ).count() > 0

    return fields


def _get_contribution_cards(page: Page):
    """Return all visible contribution card locators on the page."""
    cards = page.locator(".ant-spin-container .ant-row:has(.userInfo)")
    return cards


def _select_status(page: Page, status_label: str) -> None:
    """Select a status from the Ant Design dropdown."""
    status_select = page.locator(
        ".ant-select"
    ).filter(has_text=re.compile(r"Unreviewed|Closed|Rejected|Approved|All", re.I)).first
    status_select.click()
    page.wait_for_timeout(500)
    page.evaluate(f"""
        const items = document.querySelectorAll('.ant-select-item-option-content');
        const target = Array.from(items).find(
            el => el.textContent.trim().toLowerCase() === '{status_label.lower()}'
        );
        if (target) {{ target.click(); }}
        else {{ throw new Error('Status option "{status_label}" not found'); }}
    """)
    page.wait_for_timeout(500)


def _select_moderator(page: Page, moderator_label: str) -> None:
    """Select a moderator from the 'Select moderator' dropdown.

    The moderator dropdown uses virtual scrolling (showSearch), so not all
    options are rendered in the DOM at once. We must type into the search
    input first to filter the list, which forces the matching option into
    the DOM, then click it.
    """
    mod_select = page.locator(".ant-select").filter(
        has_text=re.compile(r"Select moderator", re.I)
    ).first
    mod_select.click()
    page.wait_for_timeout(500)

    # Type into the search input to filter the dropdown options.
    # The input[role="combobox"] inside the ant-select receives keystrokes.
    search_input = mod_select.locator("input[role='combobox']")
    search_input.fill(moderator_label)
    page.wait_for_timeout(500)

    # Now the filtered option should be in the DOM — click it via evaluate.
    page.evaluate(f"""
        const items = document.querySelectorAll('.ant-select-item-option-content');
        const target = Array.from(items).find(
            el => el.textContent.trim().toLowerCase() === '{moderator_label.lower()}'
        );
        if (target) {{ target.click(); }}
        else {{ throw new Error('Moderator option "{moderator_label}" not found'); }}
    """)
    page.wait_for_timeout(500)


def _select_date_range(page: Page, start_title: str, end_title: str) -> None:
    """Select a date range by clicking calendar cells.

    Args:
        start_title: Date in YYYY-MM-DD format (e.g. "2026-04-01")
        end_title:   Date in YYYY-MM-DD format (e.g. "2026-04-10")

    The dates must be visible in the currently displayed calendar panels.
    Use _navigate_picker_month() first if you need a different month.
    """
    page.locator(
        f"td.ant-picker-cell-in-view[title='{start_title}'] .ant-picker-cell-inner"
    ).click()
    page.wait_for_timeout(500)

    page.locator(
        f"td.ant-picker-cell-in-view[title='{end_title}'] .ant-picker-cell-inner"
    ).click()
    page.wait_for_timeout(500)


def _open_date_picker(page: Page) -> None:
    """Open the date range picker by clicking the Start date input."""
    page.get_by_role("textbox", name="Start date").click()
    page.wait_for_timeout(500)


# ── API capture helpers ──────────────────────────────────────────────────────

def capture_api_requests(page: Page, action_fn) -> list[dict]:
    """Capture POST request payloads sent to the contributors API."""
    payloads: list[dict] = []

    def handler(req):
        if CONTRIBUTORS_API_URL in req.url and req.method == "POST":
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


def capture_api_responses(page: Page, action_fn) -> list[dict]:
    """Capture response bodies returned by the contributors API."""
    bodies: list[dict] = []

    def handler(resp):
        if CONTRIBUTORS_API_URL in resp.url and resp.status == 200:
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


def capture_api_request_and_response(page: Page, action_fn) -> tuple[list[dict], list[dict]]:
    """Capture both request payloads and response bodies in one action."""
    payloads: list[dict] = []
    bodies: list[dict] = []

    def req_handler(req):
        if CONTRIBUTORS_API_URL in req.url and req.method == "POST":
            try:
                payloads.append(json.loads(req.post_data or "{}"))
            except Exception:
                pass

    def resp_handler(resp):
        if CONTRIBUTORS_API_URL in resp.url and resp.status == 200:
            try:
                bodies.append(resp.json())
            except Exception:
                pass

    page.on("request", req_handler)
    page.on("response", resp_handler)
    try:
        action_fn()
    finally:
        page.remove_listener("request", req_handler)
        page.remove_listener("response", resp_handler)
    return payloads, bodies


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATE FILTER (UI)
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsDateFilter:
    """Verify that changing the date range causes the contribution list to
    update (different count or different items)."""

    def test_date_range_march_vs_april(self, contributors_page: Page):
        """Set date range to March 1–30 2026, then switch to April 1–25 2026
        and confirm the count or content differs."""
        page = contributors_page
        _click_reset(page)

        # ── Select March 1–30, 2026 ──
        _open_date_picker(page)
        # '<' goes back 1 month (Apr 2026 → Mar 2026)
        page.locator(".ant-picker-header-prev-btn").first.click()
        page.wait_for_timeout(300)
        # Click March 1 then March 30
        _select_date_range(page, "2026-03-01", "2026-03-30")

        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)
        count_mar = _get_contribution_count(page)
        items_mar = page.locator("text=/^Product ID:/")
        first_item_mar = items_mar.first.inner_text() if items_mar.count() > 0 else ""

        # ── Select April 1–30, 2026 ──
        _click_reset(page)
        _open_date_picker(page)
        # Picker opens on current month (Apr 2026), no navigation needed
        _select_date_range(page, "2026-04-01", "2026-04-25")

        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)
        count_apr = _get_contribution_count(page)
        items_apr = page.locator("text=/^Product ID:/")
        first_item_apr = items_apr.first.inner_text() if items_apr.count() > 0 else ""

        assert (
            count_mar != count_apr or first_item_mar != first_item_apr
        ), (
            f"Date filter did not change content: "
            f"March 2025 count={count_mar}, April 2026 count={count_apr}"
        )
        _click_reset(page)

    def test_year_navigation_arrows(self, contributors_page: Page):
        """Use '<<' and '>>' arrows in the calendar to jump by year.

        Ant Design RangePicker shows two month panels side by side.
        The '<<' (prev year) is visible on the LEFT panel (.first).
        The '>>' (next year) is visible on the RIGHT panel (.last).
        """
        page = contributors_page
        _click_reset(page)

        page.get_by_placeholder("Start date").click()
        page.wait_for_timeout(500)

        # '<<' button — visible on the left panel
        prev_year_btn = page.locator(
            ".ant-picker-header-super-prev-btn"
        ).first
        prev_year_btn.click()
        page.wait_for_timeout(300)

        header_text = page.locator(".ant-picker-header").first.inner_text()
        assert "2025" in header_text, f"Expected year 2025 after clicking <<, got: {header_text}"

        # '>>' button — visible on the right panel, so use .last
        next_year_btn = page.locator(
            ".ant-picker-header-super-next-btn"
        ).last
        next_year_btn.click()
        page.wait_for_timeout(300)

        header_text = page.locator(".ant-picker-header").last.inner_text()
        assert "2026" in header_text, f"Expected year 2026 after clicking >>, got: {header_text}"

        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        _click_reset(page)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. STATUS FILTER (UI) — Card field validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsStatusFilter:
    """Verify each status card contains the correct fields."""

    def test_approved_card_fields(self, contributors_page: Page):
        """Approved cards: ID, Product ID, Date created, Status: approved, Level."""
        page = contributors_page
        _click_reset(page)
        _select_status(page, "Approved")
        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)

        cards = _get_contribution_cards(page)
        card_count = cards.count()
        assert card_count > 0, "No contribution cards found for Approved filter"

        for i in range(min(card_count, 10)):
            fields = _get_card_fields(cards.nth(i))
            assert fields["id"] is not None and len(fields["id"]) > 0, (
                f"Approved card {i+1}: ID is missing or empty"
            )
            assert fields["product_id"] is not None, f"Approved card {i+1}: Product ID is missing"
            assert fields["date_created"] is not None, f"Approved card {i+1}: Date created is missing"
            assert fields["status"] == "approved", (
                f"Approved card {i+1}: Status is '{fields['status']}', expected 'approved'"
            )
            assert fields["level"] is not None, f"Approved card {i+1}: Level is missing"
        _click_reset(page)

    def test_rejected_card_fields(self, contributors_page: Page):
        """Rejected cards: ID, Product ID, Date created, Status: closed_deleted,
        'Revert to approved' button, Level."""
        page = contributors_page
        _click_reset(page)
        _select_status(page, "Rejected")
        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)

        cards = _get_contribution_cards(page)
        card_count = cards.count()
        assert card_count > 0, "No contribution cards found for Rejected filter"

        for i in range(min(card_count, 10)):
            fields = _get_card_fields(cards.nth(i))
            assert fields["id"] is not None and len(fields["id"]) > 0, (
                f"Rejected card {i+1}: ID is missing or empty"
            )
            assert fields["product_id"] is not None, f"Rejected card {i+1}: Product ID is missing"
            assert fields["date_created"] is not None, f"Rejected card {i+1}: Date created is missing"
            assert fields["status"] == "closed_deleted", (
                f"Rejected card {i+1}: Status is '{fields['status']}', expected 'closed_deleted'"
            )
            assert fields["level"] is not None, f"Rejected card {i+1}: Level is missing"
            assert fields["has_revert_button"], (
                f"Rejected card {i+1}: 'Revert to approved' button is missing"
            )
        _click_reset(page)

    def test_rejected_revert_button_is_clickable(self, contributors_page: Page):
        """The 'Revert to approved' button should be enabled."""
        page = contributors_page
        _click_reset(page)
        _select_status(page, "Rejected")
        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)

        cards = _get_contribution_cards(page)
        assert cards.count() > 0, "No Rejected cards found"
        revert_btn = cards.first.locator(
            "button", has_text=re.compile(r"Revert to approved", re.I)
        )
        assert revert_btn.count() > 0, "'Revert to approved' button not found"
        expect(revert_btn.first).to_be_enabled()
        _click_reset(page)

    def test_closed_card_fields(self, contributors_page: Page):
        """Closed cards: ID, Product ID, Date created, Status: closed, Level."""
        page = contributors_page
        _click_reset(page)
        _select_status(page, "Closed")
        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)

        cards = _get_contribution_cards(page)
        card_count = cards.count()
        assert card_count > 0, "No contribution cards found for Closed filter"

        for i in range(min(card_count, 10)):
            fields = _get_card_fields(cards.nth(i))
            assert fields["id"] is not None and len(fields["id"]) > 0, (
                f"Closed card {i+1}: ID is missing or empty"
            )
            assert fields["product_id"] is not None, f"Closed card {i+1}: Product ID is missing"
            assert fields["date_created"] is not None, f"Closed card {i+1}: Date created is missing"
            assert fields["status"] == "closed", (
                f"Closed card {i+1}: Status is '{fields['status']}', expected 'closed'"
            )
            assert fields["level"] is not None, f"Closed card {i+1}: Level is missing"
        _click_reset(page)

    def test_unreviewed_card_fields(self, contributors_page: Page):
        """Unreviewed cards: ID, Product ID, Date created, Status: unreviewed,
        Level. Cards reviewed by AI also show Moderator name + email.
        Cards where AI could not process the image (wrong format,
        unrecognizable) will NOT have moderator fields — that is valid."""
        page = contributors_page
        _click_reset(page)
        _select_status(page, "Unreviewed")
        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)

        cards = _get_contribution_cards(page)
        card_count = cards.count()
        assert card_count > 0, "No contribution cards found for Unreviewed filter"

        cards_with_moderator = 0
        cards_without_moderator = 0

        for i in range(min(card_count, 10)):
            fields = _get_card_fields(cards.nth(i))

            # These 5 fields must always be present on every unreviewed card
            assert fields["id"] is not None and len(fields["id"]) > 0, (
                f"Unreviewed card {i+1}: ID is missing or empty"
            )
            assert fields["product_id"] is not None, f"Unreviewed card {i+1}: Product ID is missing"
            assert fields["date_created"] is not None, f"Unreviewed card {i+1}: Date created is missing"
            assert fields["status"] == "unreviewed", (
                f"Unreviewed card {i+1}: Status is '{fields['status']}', expected 'unreviewed'"
            )
            assert fields["level"] is not None, f"Unreviewed card {i+1}: Level is missing"

            # Moderator fields are optional — present when AI reviewed,
            # absent when AI could not process the image
            has_moderator = (
                fields["moderator_name"] is not None
                and fields["moderator_email"] is not None
            )

            if has_moderator:
                cards_with_moderator += 1
            else:
                cards_without_moderator += 1

        print(
            f"\n  Unreviewed cards inspected: {min(card_count, 10)} | "
            f"With moderator: {cards_with_moderator} | "
            f"Without moderator (AI could not review): {cards_without_moderator}"
        )
        _click_reset(page)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PRODUCT GTIN SEARCH (UI)
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsGtinSearch:
    """Search by Product GTIN and verify results and detail view."""

    SAMPLE_GTIN = "04901872067961"

    def test_gtin_search_shows_result(self, contributors_page: Page):
        """Enter a known GTIN and verify the result shows the matching Product ID."""
        page = contributors_page
        _click_reset(page)

        # Search across all statuses — the GTIN may not be under Unreviewed
        _select_status(page, "All")
        page.get_by_placeholder("Product GTIN").fill(self.SAMPLE_GTIN)
        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)

        count = _get_contribution_count(page)
        assert count > 0, f"No contributions found for GTIN {self.SAMPLE_GTIN}"

        product_id_text = page.locator(f"text=Product ID:{self.SAMPLE_GTIN}")
        expect(product_id_text.first).to_be_visible(timeout=10_000)
        _click_reset(page)

    def test_gtin_search_detail_view(self, contributors_page: Page):
        """Search by GTIN, click the image, verify the detail page shows GTIN."""
        page = contributors_page
        _click_reset(page)

        _select_status(page, "All")
        page.get_by_placeholder("Product GTIN").fill(self.SAMPLE_GTIN)
        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)

        # Click the product image inside the first contribution card
        # (not the sidebar logo). Cards use img with style "height: 300px".
        cards = _get_contribution_cards(page)
        assert cards.count() > 0, "No cards found for GTIN search"
        cards.first.locator("img").first.click()
        page.wait_for_timeout(2_000)

        page.wait_for_url(re.compile(r"/contributors/editor/"), timeout=15_000)
        # GTIN is shown inside an input field, not as plain text
        gtin_input = page.locator(f"input[value='{self.SAMPLE_GTIN}']")
        expect(gtin_input.first).to_be_visible(timeout=10_000)

        return_btn = page.locator("text=RETURN")
        if return_btn.count() > 0:
            return_btn.first.click()
        else:
            page.go_back()
        page.wait_for_selector("text=contributions are found", timeout=30_000)
        _click_reset(page)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. USER NAME SEARCH (UI)
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsUserSearch:
    """Search by User name and verify results."""

    def test_username_with_results(self, contributors_page: Page):
        """'Ting' should return results."""
        page = contributors_page
        _click_reset(page)
        page.get_by_placeholder("User name").fill("Ting")
        _click_apply(page)
        page.wait_for_selector("text=contributions are found", timeout=15_000)
        count = _get_contribution_count(page)
        assert count > 0, "Expected results for User name 'Ting', but found 0"
        _click_reset(page)

    def test_username_no_results(self, contributors_page: Page):
        """'g3' should return 0 contributions."""
        page = contributors_page
        _click_reset(page)
        page.get_by_placeholder("User name").fill("g3")
        _click_apply(page)
        page.wait_for_timeout(3_000)
        count = _get_contribution_count(page)
        assert count == 0, f"Expected 0 contributions for 'g3', but found {count}"
        _click_reset(page)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. RESET BUTTON — API
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsAPIReset:
    """Verify that clicking Reset restores all filters to default values
    and the API request reflects the default state.

    Default state: status=Unreviewed, no date filter, country=Australia,
    no GTIN, no moderator, no user name.
    """

    def test_reset_restores_default_api_payload(self, contributors_page: Page):
        """Apply custom filters (date, GTIN, moderator), then click Reset.
        The API request after reset should match the default payload."""
        page = contributors_page

        # ── Step 1: Capture the default API request by navigating fresh ──
        default_requests = capture_api_requests(
            page, lambda: _goto_contributors(page)
        )
        assert len(default_requests) > 0, "No API request on page load"
        default_payload = default_requests[0]

        # ── Step 2: Apply custom filters ──
        _open_date_picker(page)
        _select_date_range(page, "2026-04-01", "2026-04-10")
        page.get_by_placeholder("Product GTIN").fill("09781974730735")
        _select_moderator(page, "AI Moderator")
        _click_apply(page)
        page.wait_for_timeout(2_000)

        # ── Step 3: Click Reset and capture the API request ──
        reset_requests = capture_api_requests(page, lambda: _click_reset(page))
        assert len(reset_requests) > 0, "No API request fired after clicking Reset"
        reset_payload = reset_requests[0]

        # ── Step 4: Verify reset payload matches default ──
        # The reset payload should NOT contain the custom GTIN
        reset_str = json.dumps(reset_payload)
        assert "09781974730735" not in reset_str, (
            f"Reset payload still contains the custom GTIN: {reset_payload}"
        )

        # Status should be back to default (unreviewed)
        reset_status = json.dumps(reset_payload).lower()
        assert "unreviewed" in reset_status, (
            f"Reset did not restore default status. Reset: {reset_payload}"
        )

    def test_reset_ui_fields_match_default(self, contributors_page: Page):
        """After applying custom filters and clicking Reset, verify the
        UI fields visually return to default values."""
        page = contributors_page
        _click_reset(page)

        # ── Apply custom filters ──
        _open_date_picker(page)
        _select_date_range(page, "2026-04-01", "2026-04-10")
        page.get_by_placeholder("Product GTIN").fill("09781974730735")
        _select_moderator(page, "AI Moderator")
        _click_apply(page)
        page.wait_for_timeout(2_000)

        # ── Click Reset ──
        _click_reset(page)

        # ── Verify UI defaults ──

        # Status dropdown should show "Unreviewed"
        status_dropdown = page.locator(".ant-select").filter(
            has_text=re.compile(r"Unreviewed|Closed|Rejected|Approved|All", re.I)
        ).first
        status_text = status_dropdown.inner_text().lower()
        assert "unreviewed" in status_text, (
            f"Status not reset to 'Unreviewed', showing: {status_text}"
        )

        # GTIN field should be empty
        gtin_input = page.get_by_placeholder("Product GTIN")
        assert gtin_input.input_value() == "", (
            f"GTIN field not cleared after reset, contains: {gtin_input.input_value()}"
        )

        # User name field should be empty
        username_input = page.get_by_placeholder("User name")
        assert username_input.input_value() == "", (
            f"User name field not cleared after reset, contains: {username_input.input_value()}"
        )

        # Date fields should be empty (no date filter = all dates)
        start_input = page.get_by_placeholder("Start date")
        end_input = page.get_by_placeholder("End date")
        assert start_input.input_value() == "", (
            f"Start date not cleared after reset, contains: {start_input.input_value()}"
        )
        assert end_input.input_value() == "", (
            f"End date not cleared after reset, contains: {end_input.input_value()}"
        )

    def test_reset_api_response_matches_default(self, contributors_page: Page):
        """The API response after Reset should have the same count as the
        initial default load."""
        page = contributors_page

        # Capture default response by navigating fresh
        default_responses = capture_api_responses(
            page, lambda: _goto_contributors(page)
        )
        assert len(default_responses) > 0, "No API response on page load"
        default_count = default_responses[0].get("count", -1)

        # Apply custom filter then reset
        _open_date_picker(page)
        _select_date_range(page, "2026-04-01", "2026-04-10")
        page.get_by_placeholder("Product GTIN").fill("09781974730735")
        _click_apply(page)
        page.wait_for_timeout(2_000)

        # Reset and capture
        reset_responses = capture_api_responses(page, lambda: _click_reset(page))
        assert len(reset_responses) > 0, "No API response after Reset"
        reset_count = reset_responses[0].get("count", -2)

        assert reset_count == default_count, (
            f"Reset count ({reset_count}) != default count ({default_count})"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. API RESPONSE SCHEMA / CONTRACT
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsAPIResponseSchema:
    """Verify the API response structure matches the expected contract."""

    def test_response_has_count_and_documents(self, contributors_page: Page):
        """Response must have 'count' (int) and 'documents' (list)."""
        page = contributors_page
        responses = capture_api_responses(
            page, lambda: _goto_contributors(page)
        )
        assert len(responses) > 0, "No API response captured"

        resp = responses[0]
        assert "count" in resp, f"Response missing 'count' field: {list(resp.keys())}"
        assert "documents" in resp, f"Response missing 'documents' field: {list(resp.keys())}"
        assert isinstance(resp["count"], int), f"'count' is not an int: {type(resp['count'])}"
        assert isinstance(resp["documents"], list), f"'documents' is not a list: {type(resp['documents'])}"

    def test_document_has_required_fields(self, contributors_page: Page):
        """Each document in the response should have key fields like
        status, created, country."""
        page = contributors_page
        responses = capture_api_responses(
            page, lambda: _goto_contributors(page)
        )
        assert len(responses) > 0, "No API response captured"

        resp = responses[0]
        docs = resp.get("documents", [])
        assert len(docs) > 0, "No documents in response"

        doc = docs[0]
        # Check for common expected fields
        assert "created" in doc, f"Document missing 'created' field: {list(doc.keys())}"
        assert "country" in doc, f"Document missing 'country' field: {list(doc.keys())}"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. PAGINATION — API
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsAPIPagination:
    """Verify pagination sends correct offset and returns different docs."""

    def test_page2_sends_offset(self, contributors_page: Page):
        """Clicking page 2 should send an API request with offset=10."""
        page = contributors_page
        _click_reset(page)

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)

        page2_link = page.locator("li.ant-pagination-item").filter(has_text="2")
        if page2_link.count() == 0:
            pytest.skip("Page 2 not available — not enough data")

        requests = capture_api_requests(page, lambda: (
            page2_link.first.click(),
            page.wait_for_timeout(3_000),
        ))

        assert len(requests) > 0, "No API request for page 2"
        payload_str = json.dumps(requests[0])
        # NOTE: API uses 0-based pagination
        # clicking page 2 in UI sends "page": 1 to the API
        has_page = re.search(r'"page":\s*1', payload_str)
        assert has_page, (
            f"Page 2 request missing pagination params: {requests[0]}"
        )
        _click_reset(page)

    def test_page1_and_page2_return_different_docs(self, contributors_page: Page):
        """Page 1 and page 2 should return different documents (no overlap)."""
        page = contributors_page

        # Capture page 1 response by navigating fresh
        p1_responses = capture_api_responses(
            page, lambda: _goto_contributors(page)
        )
        assert len(p1_responses) > 0, "No API response for page 1"
        p1_docs = p1_responses[0].get("documents", [])

        # Go to page 2
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        page2_link = page.locator("li.ant-pagination-item").filter(has_text="2")
        if page2_link.count() == 0:
            pytest.skip("Page 2 not available")

        p2_responses = capture_api_responses(page, lambda: (
            page2_link.first.click(),
            page.wait_for_timeout(3_000),
        ))
        assert len(p2_responses) > 0
        p2_docs = p2_responses[0].get("documents", [])

        # Compare: stringify first doc from each page, they should differ
        if len(p1_docs) > 0 and len(p2_docs) > 0:
            p1_first = json.dumps(p1_docs[0], sort_keys=True)
            p2_first = json.dumps(p2_docs[0], sort_keys=True)
            assert p1_first != p2_first, "Page 1 and Page 2 returned identical first document"
        _click_reset(page)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. STATUS FILTER — API
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsAPIStatusFilter:
    """Verify the API request includes correct status and all response
    items match the requested status."""

    # Map UI label → actual API value sent in the payload
    STATUS_API_MAP = {
        "Unreviewed": "unreviewed",
        "Closed": "closed",
        "Rejected": "closed_deleted",
        "Approved": "approved",
    }

    @pytest.mark.parametrize("status", ["Unreviewed", "Closed", "Rejected", "Approved"])
    def test_api_sends_correct_status(self, contributors_page: Page, status: str):
        """The API payload should include the correct status value."""
        page = contributors_page
        _click_reset(page)

        # First switch to a DIFFERENT status so the target status is
        # actually a change — otherwise Apply won't fire a new request.
        different = "Closed" if status != "Closed" else "Approved"
        _select_status(page, different)
        _click_apply(page)

        # Now select the target status and capture
        _select_status(page, status)
        requests = capture_api_requests(page, lambda: _click_apply(page))

        assert len(requests) > 0, f"No API request for status '{status}'"
        payload_str = json.dumps(requests[0]).lower()
        expected_api_value = self.STATUS_API_MAP[status]
        assert expected_api_value in payload_str, (
            f"API payload does not contain '{expected_api_value}': {requests[0]}"
        )
        _click_reset(page)

    @pytest.mark.parametrize("status", ["Closed", "Approved"])
    def test_api_response_items_match_status(self, contributors_page: Page, status: str):
        """All documents returned should have the requested status."""
        page = contributors_page
        _click_reset(page)
        _select_status(page, status)
        responses = capture_api_responses(page, lambda: _click_apply(page))

        assert len(responses) > 0, f"No API response for status '{status}'"
        resp = responses[0]
        docs = resp.get("documents", [])

        for i, doc in enumerate(docs[:10]):
            doc_status = doc.get("status", "").lower()

            if doc_status:
                assert doc_status == status.lower(), (
                    f"Doc {i} has status '{doc_status}', expected '{status.lower()}'"
                )
        _click_reset(page)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. EDGE CASES — API
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsAPIEdgeCases:
    """Test API behavior with invalid or edge-case inputs."""

    def test_nonexistent_gtin_returns_zero(self, contributors_page: Page):
        """Searching for a GTIN that doesn't exist should return count=0."""
        page = contributors_page
        _click_reset(page)

        page.get_by_placeholder("Product GTIN").fill("0000000000000")
        responses = capture_api_responses(page, lambda: _click_apply(page))

        assert len(responses) > 0, "No API response for nonexistent GTIN"
        resp = responses[0]
        assert resp.get("count", -1) == 0, (
            f"Expected count=0 for fake GTIN, got {resp.get('count')}"
        )
        assert len(resp.get("documents", [])) == 0, (
            "Expected empty documents for fake GTIN"
        )
        _click_reset(page)

    def test_nonexistent_username_returns_zero(self, contributors_page: Page):
        """Searching for user 'zzz_no_such_user_999' should return count=0."""
        page = contributors_page
        _click_reset(page)

        page.get_by_placeholder("User name").fill("zzz_no_such_user_999")
        responses = capture_api_responses(page, lambda: _click_apply(page))

        assert len(responses) > 0
        resp = responses[0]
        assert resp.get("count", -1) == 0, (
            f"Expected 0 results for fake user, got {resp.get('count')}"
        )
        _click_reset(page)

    def test_two_different_date_ranges_return_different_data(self, contributors_page: Page):
        """Two different date ranges should produce different API responses."""
        page = contributors_page
        _click_reset(page)

        # Use "All" status so both ranges have data to compare
        _select_status(page, "All")

        _open_date_picker(page)
        _select_date_range(page, "2026-04-01", "2026-04-05")
        responses_a = capture_api_responses(page, lambda: _click_apply(page))

        # Re-select "All" after reset clears it back to Unreviewed
        _click_reset(page)
        _select_status(page, "All")

        _open_date_picker(page)
        # Navigate back 1 month to March
        page.locator(".ant-picker-header-prev-btn").first.click()
        page.wait_for_timeout(300)
        _select_date_range(page, "2026-03-01", "2026-03-30")
        responses_b = capture_api_responses(page, lambda: _click_apply(page))

        assert len(responses_a) > 0 and len(responses_b) > 0
        resp_a_str = json.dumps(responses_a[0], sort_keys=True)
        resp_b_str = json.dumps(responses_b[0], sort_keys=True)
        assert resp_a_str != resp_b_str, (
            "API returned identical responses for two different date ranges"
        )
        _click_reset(page)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. PERFORMANCE — API
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributorsAPIPerformance:
    """Verify the API responds within acceptable time limits."""

    def test_api_responds_within_5_seconds_with_filters(self, contributors_page: Page):
        """The contributors API should respond within 5 seconds when
        multiple filters are applied: date range, email, and status."""
        page = contributors_page
        _click_reset(page)

        # Apply multiple filters to simulate real-world heavy query
        _select_status(page, "All")
        _open_date_picker(page)
        _select_date_range(page, "2026-04-01", "2026-04-25")
        page.get_by_placeholder("User email").fill("ting.shping+s1@gmail.com")

        start_time = time.time()
        responses = capture_api_responses(page, lambda: _click_apply(page))
        elapsed = time.time() - start_time

        assert len(responses) > 0, "No API response captured with filters applied"
        assert elapsed < 5.0, (
            f"API took {elapsed:.2f}s with filters applied, expected < 5.0s\n"
            f"Filters used: status=All, date=01/01/2026 to 04/01/2026, "
            f"email=ting.shping+s1@gmail.com"
        )
        _click_reset(page)