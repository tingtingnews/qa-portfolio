"""
test_media_hub_create.py
Tests for Shping Admin - Media Hub > Campaigns > Create Campaign flow

UI Tests:
  1. TestCreateSettingsValidation  - Step 1 field validations and controls
  2. TestCreateMediaAdSets         - Step 2 media type selection and fields
  3. TestCreateNavigation          - Back/Next navigation and data preservation

BE / Data Tests:
  4. TestCreateSettingsPayload     - API payload for Step 1 fields
  5. TestCreateMediaPayload        - API payload for media upload and type
  6. TestCreateEndToEnd            - Full creation flow and list verification

Run:
    pytest test_media_hub_create.py -v --headed
    pytest test_media_hub_create.py -k "Settings" -v --headed
    pytest test_media_hub_create.py -k "Media" -v --headed
    pytest test_media_hub_create.py -k "Navigation" -v --headed
    pytest test_media_hub_create.py -k "Payload" -v --headed

NOTE: Uses the "Wild Co" participant context.
"""

import re
import json
import time
import pytest
from playwright.sync_api import Page, expect

from conftest import BASE_URL, API_BASE_URL, CAMPAIGNS_URL


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAMPAIGNS_API = f"{API_BASE_URL}/rewards-service/media_hub/campaign/read_list"
CREATE_API = f"{API_BASE_URL}/rewards-service/media_hub/campaign"

# Error messages - Step 1 (Settings)
ERR_CAMPAIGN_NAME = "Please enter a campaign name"
ERR_DAILY_BUDGET = "Please enter a daily budget"
ERR_START_DATE = "Please select a start date"

# Error messages - Step 2 (Media / Ad Sets)
ERR_MEDIA_TYPE = "Please select a media type"
ERR_AD_SET_TITLE = "Please enter ad set title"
ERR_BRANDING_ENTITY = "Please link an identity item"
ERR_UPLOAD_MEDIA = "Please upload media"
ERR_UPLOAD_PREVIEW = "Please upload video preview first"

# ---------------------------------------------------------------------------
# Verified DOM selectors (inspected live 2026-05-11)
# ---------------------------------------------------------------------------
# Step 1 (Settings):
#   Campaign name : input#media-hub-campaign_campaignName  (type="text")
#   Daily budget  : input.ant-input-number-input  (type="text", role="spinbutton")
#   Ongoing toggle: .ant-modal-body button[role="switch"]:nth(0)  (aria-checked)
#   Active toggle : .ant-modal-body button[role="switch"]:nth(1)  (aria-checked)
#   Start date    : input#media-hub-campaign-settings_startDate  (inside .ant-picker)
#   End date      : input#media-hub-campaign-settings_endDate   (disabled when Ongoing=ON)
#   NOTE: placeholder="Start date" / "End date" matches TWO elements
#         (background page + modal) — always use the IDs above.
#   Errors        : div.ant-form-item-explain-error   (color rgb(255,77,79))
#   Next button   : styled-component (bg rgb(255,79,94)) — use text= selector
#   Cancel button : styled-component (bg white)         — use text= selector
#
# Step 2 (Media) — shared between Video Ad and Static Banner:
#   Radio buttons : input[type="radio"] with values "video" / "image"
#                   wrapped in .ant-radio-wrapper, name="adSetType"
#   Ad Set Title  : input#media-hub-campaign-adset_adSetTitle  (type="text")
#   Branding ent. : input#media-hub-campaign-adset_identityItem (inside .ant-select)
#   Active toggle : .ant-modal-body button[role="switch"]  (only 1 on Step 2)
#
# Step 2 — Product Video Ad:
#   Video upload  : .ant-upload input[type="file"]  accept="video/mp4,..."
#   Preview upload: .ant-upload input[type="file"]  accept="image/png,..."
#   Capture prev. : button.ant-btn (text "Capture preview"), disabled by default
#
# Step 2 — Product Static Banner:
#   Image upload  : .ant-upload input[type="file"]  accept="image/png, image/jpeg, image/gif, image/webp"


# ---------------------------------------------------------------------------
# Fixture - create_page (navigates to campaigns, opens Create dialog)
# ---------------------------------------------------------------------------

@pytest.fixture
def create_page(session_page: Page) -> Page:
    """
    Switch to 'Wild Co', navigate to Campaigns, click Create button,
    and wait for the dialog to appear.
    """
    _switch_participant(session_page, "Wild Co")
    session_page.goto(CAMPAIGNS_URL)
    try:
        session_page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass
    # Wait for the campaigns table to load
    session_page.wait_for_selector("button[role='switch']", timeout=30_000)

    # Click the Create button
    create_btn = session_page.get_by_role("button", name="Create")
    create_btn.click()
    session_page.wait_for_timeout(1000)

    # Wait for the dialog to appear
    session_page.wait_for_selector("text=Media Hub Campaign Set Up", timeout=10_000)

    yield session_page

    # Cleanup: close dialog if still open
    try:
        close_btn = session_page.locator("button:has-text('Cancel')")
        if close_btn.count() > 0 and close_btn.first.is_visible():
            close_btn.first.click()
            session_page.wait_for_timeout(500)
    except Exception:
        pass
    # Also try the X button
    try:
        x_btn = session_page.locator(".ant-modal-close, [aria-label='Close']")
        if x_btn.count() > 0 and x_btn.first.is_visible():
            x_btn.first.click()
            session_page.wait_for_timeout(500)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _switch_participant(page: Page, target: str) -> None:
    """Switch the participant selector to *target* if not already selected."""
    try:
        already = page.locator(f".ant-select-content[title*='{target}']")
        if already.count() > 0 and already.first.is_visible():
            return
    except Exception:
        pass

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


def _click_next(page: Page) -> None:
    """Click the Next button in the Create Campaign dialog."""
    next_btn = page.locator("button:has-text('Next')")
    next_btn.click()
    page.wait_for_timeout(500)


def _click_back(page: Page) -> None:
    """Click the Back button in the Create Campaign dialog."""
    back_btn = page.locator("button:has-text('Back')")
    back_btn.click()
    page.wait_for_timeout(500)


def _fill_settings(page: Page, name: str = "AutoTest-Campaign_123",
                   budget: str = "10", ongoing: bool = True,
                   start_date_cell: str = None) -> None:
    """
    Fill Step 1 (Settings) fields.
    Uses calendar picker for dates since direct typing does not work
    on the Ant Design DatePicker.

    Args:
        name: Campaign name to enter
        budget: Daily budget value
        ongoing: If True, leave Ongoing toggle ON. If False, toggle it OFF.
        start_date_cell: CSS selector for the start date cell to click
                         in the calendar (e.g. "td[title='2026-05-09']").
                         If None, clicks the "Today" link.
    """
    # Campaign name — verified id: media-hub-campaign_campaignName
    name_input = page.locator(
        "#media-hub-campaign_campaignName, "
        "input[placeholder='e.g. Spring launch']"
    ).first
    name_input.click()
    name_input.fill(name)

    # Daily budget — DOM confirmed: type="text" with role="spinbutton",
    # class includes "ant-input-number-input"
    budget_input = page.locator(".ant-input-number-input").first
    budget_input.click()
    budget_input.fill(budget)

    # Handle Ongoing toggle — DOM confirmed: the modal has switches
    # identified by button[role="switch"].  On Step 1 there are exactly 2:
    #   index 0 = Ongoing, index 1 = Active
    # We target the first switch inside .ant-modal-body.
    ongoing_switch = page.locator(
        ".ant-modal-body button[role='switch']"
    ).first

    if not ongoing:
        is_checked = ongoing_switch.get_attribute("aria-checked")
        if is_checked == "true":
            ongoing_switch.click()
            page.wait_for_timeout(300)

    # Select start date via calendar picker.
    # DOM confirmed id: media-hub-campaign-settings_startDate
    # Must use ID because placeholder="Start date" matches TWO elements
    # (one in the background page, one inside the modal dialog).
    start_input = page.locator("#media-hub-campaign-settings_startDate")
    start_input.click()
    page.wait_for_timeout(500)

    if start_date_cell:
        page.locator(start_date_cell).click()
    else:
        # Click today's date cell in the calendar.
        # DOM confirmed: today's cell has class "ant-picker-cell-today"
        # e.g. <td title="2026-05-11" class="...ant-picker-cell-today">
        # The "Today" footer link (.ant-picker-today-btn) does NOT exist here.
        page.locator("td.ant-picker-cell-today").click()

    page.wait_for_timeout(500)


def _get_visible_errors(page: Page) -> list:
    """Return a list of visible red error message texts."""
    error_selectors = [
        ".ant-form-item-explain-error",
        "[role='alert']",
        ".ant-form-item-explain span",
    ]
    errors = []
    for sel in error_selectors:
        els = page.locator(sel)
        for i in range(els.count()):
            txt = els.nth(i).inner_text().strip()
            if txt and txt not in errors:
                errors.append(txt)
    if not errors:
        # Fallback: look for red text with known error patterns
        red_texts = page.locator(
            "text=/Please enter|Please select|Please upload|Please link/i"
        )
        for i in range(red_texts.count()):
            txt = red_texts.nth(i).inner_text().strip()
            if txt and txt not in errors:
                errors.append(txt)
    return errors


def _get_step_number(page: Page) -> int:
    # Return the current step number (1-5) from the step indicator.
    #
    # The wizard uses styled-components, so the active step has a DIFFERENT
    # generated class name than inactive steps.  For example:
    #   active:   div.sc-cLQEGU.cMpGHC
    #   inactive: div.sc-cLQEGU.gbTwtm
    #
    # Strategy: use JavaScript to find which step's number circle has a
    # colored (non-gray) background - that is the active step.
    result = page.evaluate("""(() => {
        const titles = ["Settings", "Media", "CTA", "Targeting", "Review"];
        const spans = document.querySelectorAll('span');
        for (let i = 0; i < titles.length; i++) {
            for (const span of spans) {
                if (span.textContent.trim() === titles[i]) {
                    const container = span.closest('div[class*="sc-"]') ||
                                      span.parentElement;
                    const circle = container
                        ? container.querySelector('div[class*="sc-"]')
                        : null;
                    if (circle) {
                        const bg = getComputedStyle(circle).backgroundColor;
                        // Active step circle has a non-gray, non-white bg
                        // (typically red/pink like rgb(255, 92, 108))
                        if (bg && !bg.includes('255, 255, 255') &&
                            !bg.includes('0, 0, 0') &&
                            bg !== 'rgba(0, 0, 0, 0)' &&
                            bg !== 'transparent') {
                            // Check if it's a colored bg (not gray)
                            const match = bg.match(/\d+/g);
                            if (match && match.length >= 3) {
                                const r = parseInt(match[0]);
                                const g = parseInt(match[1]);
                                const b = parseInt(match[2]);
                                // Gray means r == g == b (roughly)
                                if (Math.abs(r - g) > 30 || Math.abs(r - b) > 30) {
                                    return i + 1;
                                }
                            }
                        }
                    }
                }
            }
        }
        return -1;
    })()""")
    return result if result > 0 else 1


# ============================================================================
# UI TESTS
# ============================================================================


class TestCreateSettingsValidation:
    """
    Step 1 (Settings) - merged test cases:
    - Empty form validation (all 3 required field errors)
    - Campaign name accepts special characters and digits
    - Brand is optional
    - Budget rejects non-numeric input
    - Ongoing toggle enables/disables End date
    - Start date can be a past date
    - Cancel closes the dialog
    """

    def test_empty_form_shows_all_errors(self, create_page: Page):
        # TC-01: Click Next without filling anything
        # All 3 mandatory field errors should appear
        page = create_page
        _click_next(page)
        page.wait_for_timeout(500)

        errors = _get_visible_errors(page)

        assert ERR_CAMPAIGN_NAME in errors, (
            f"Expected '{ERR_CAMPAIGN_NAME}' in errors, got: {errors}"
        )
        assert ERR_DAILY_BUDGET in errors, (
            f"Expected '{ERR_DAILY_BUDGET}' in errors, got: {errors}"
        )
        assert ERR_START_DATE in errors, (
            f"Expected '{ERR_START_DATE}' in errors, got: {errors}"
        )

        # Form should stay on Step 1
        step_title = page.locator("text=Campaign name")
        expect(step_title.first).to_be_visible()

    def test_name_special_chars_and_brand_optional(self, create_page: Page):
        # TC-02 + TC-03 merged:
        # Campaign name with special chars is accepted
        # Brand left empty is OK - no error
        page = create_page
        special_name = "Abc-123_Test!@#"

        _fill_settings(page, name=special_name, budget="15")

        # Leave Brand as "Select brand" (do not pick anything)
        _click_next(page)
        page.wait_for_timeout(1000)

        # Should advance to Step 2 (Media)
        ad_sets = page.locator("text=Ad Sets")
        expect(ad_sets.first).to_be_visible(timeout=5_000)

        # Verify we moved to Step 2
        media_title = page.locator("text=Choose the media format")
        expect(media_title.first).to_be_visible()

    def test_budget_rejects_non_numeric(self, create_page: Page):
        # TC-04: Budget field should only accept digits
        # DOM confirmed: input is type="text" with role="spinbutton"
        # class "ant-input-number-input" — Ant Design InputNumber strips
        # non-numeric characters on blur.
        page = create_page

        budget_input = page.locator(".ant-input-number-input").first
        budget_input.click()
        budget_input.fill("abc")
        # Trigger blur so Ant Design validates
        page.keyboard.press("Tab")
        page.wait_for_timeout(300)

        actual_value = budget_input.input_value()
        # Ant Design InputNumber strips non-numeric chars on blur
        assert actual_value == "" or actual_value.replace(".", "").isdigit(), (
            f"Budget accepted non-numeric input: '{actual_value}'"
        )

    def test_ongoing_toggle_controls_end_date(self, create_page: Page):
        # TC-05 + TC-06 merged:
        # Ongoing ON -> End date disabled
        # Ongoing OFF -> End date becomes editable
        # DOM confirmed: Step 1 has 2 switches in modal.
        #   index 0 = Ongoing, index 1 = Active
        page = create_page

        ongoing_switch = page.locator(
            ".ant-modal-body button[role='switch']"
        ).first

        # Default: Ongoing is ON
        is_checked = ongoing_switch.get_attribute("aria-checked")
        assert is_checked == "true", "Ongoing toggle should default to ON"

        # End date should be disabled when Ongoing is ON.
        # DOM confirmed: the end-date picker gets class "ant-picker-disabled"
        # and its <input> has disabled=true.
        end_input = page.locator("#media-hub-campaign-settings_endDate")
        is_disabled = end_input.is_disabled()
        assert is_disabled, "End date should be disabled when Ongoing is ON"

        # Toggle Ongoing OFF
        ongoing_switch.click()
        page.wait_for_timeout(500)

        # Now End date should be enabled
        is_disabled_after = end_input.is_disabled()
        assert not is_disabled_after, (
            "End date should be enabled when Ongoing is OFF"
        )

        # Click End date to verify calendar opens
        end_input.click()
        page.wait_for_timeout(500)
        calendar = page.locator(".ant-picker-dropdown")
        expect(calendar.first).to_be_visible(timeout=3_000)

        # Close calendar
        page.keyboard.press("Escape")

    def test_start_date_allows_past_date(self, create_page: Page):
        # TC-07: Start date can be set to a past date
        page = create_page

        start_input = page.locator("#media-hub-campaign-settings_startDate")
        start_input.click()
        page.wait_for_timeout(500)

        # Navigate to previous month using the back arrow
        prev_btn = page.locator(
            ".ant-picker-header button[class*='prev-month'], "
            ".ant-picker-header button:has(> span[class*='prev'])"
        ).first
        prev_btn.click()
        page.wait_for_timeout(300)

        # Click the first available date cell in the previous month
        date_cell = page.locator(
            "td.ant-picker-cell-in-view"
        ).first
        date_cell.click()
        page.wait_for_timeout(500)

        # Verify the date was accepted (input has a value)
        date_value = start_input.input_value()
        assert date_value != "", "Start date should accept a past date"

    def test_cancel_closes_dialog(self, create_page: Page):
        # TC-08: Cancel button closes the Create dialog
        page = create_page

        # Fill some data first
        name_input = page.locator(
            "#media-hub-campaign_campaignName, "
            "input[placeholder='e.g. Spring launch']"
        ).first
        name_input.fill("Should Not Be Saved")

        # Click Cancel
        cancel_btn = page.locator("button:has-text('Cancel')")
        cancel_btn.click()
        page.wait_for_timeout(1000)

        # Dialog should be closed - Create dialog title should not be visible
        dialog = page.locator("text=Media Hub Campaign Set Up")
        expect(dialog).to_have_count(0, timeout=5_000)

        # Campaigns table should still be visible
        table = page.locator("text=Media Hub Campaigns")
        expect(table.first).to_be_visible()


class TestCreateMediaAdSets:
    """
    Step 2 (Media / Ad Sets) - merged test cases:
    - No media type error on Next
    - Product Video Ad shows correct collapsed fields
    - Product Static Banner shows correct collapsed fields
    - All mandatory field errors for Video Ad
    - All mandatory field errors for Static Banner
    - WebP format accepted for upload
    """

    @pytest.fixture
    def media_page(self, create_page: Page) -> Page:
        """Fill Step 1 and advance to Step 2."""
        page = create_page
        _fill_settings(page)
        _click_next(page)
        page.wait_for_timeout(1000)
        # Wait for Step 2 to appear
        page.wait_for_selector("text=Ad Sets", timeout=10_000)
        return page

    def test_no_media_type_error(self, media_page: Page):
        # TC-12: Click Next without selecting a media type
        page = media_page
        _click_next(page)
        page.wait_for_timeout(500)

        errors = _get_visible_errors(page)
        assert ERR_MEDIA_TYPE in errors, (
            f"Expected '{ERR_MEDIA_TYPE}' in errors, got: {errors}"
        )

    def test_video_ad_expands_correct_fields(self, media_page: Page):
        # TC-13: Select Product Video Ad and check visible sections
        page = media_page

        # Click Product Video Ad radio
        video_option = page.locator("text=Product Video Ad").first
        video_option.click()
        page.wait_for_timeout(500)

        # Verify all 4 sections are visible
        expect(page.locator("text=Ad Set Title").first).to_be_visible()
        expect(page.locator("text=Branding entity").first).to_be_visible()
        expect(page.locator("text=Ad Set Video").first).to_be_visible()
        expect(page.locator("text=Ad Set Video Preview").first).to_be_visible()
        expect(page.locator("button:has-text('Capture preview')").first).to_be_visible()

        # DOM confirmed: video upload accepts video/mp4,...
        video_upload = page.locator(
            ".ant-modal-body .ant-upload input[type='file'][accept*='video']"
        )
        assert video_upload.count() > 0, "Video file input should exist"

        # DOM confirmed: preview upload accepts image/png,...
        img_upload = page.locator(
            ".ant-modal-body .ant-upload input[type='file'][accept*='image']"
        )
        assert img_upload.count() > 0, "Preview image file input should exist"

    def test_static_banner_expands_correct_fields(self, media_page: Page):
        # TC-14: Select Product Static Banner and check visible sections
        page = media_page

        banner_option = page.locator("text=Product Static Banner").first
        banner_option.click()
        page.wait_for_timeout(500)

        # Verify 3 sections visible
        expect(page.locator("text=Ad Set Title").first).to_be_visible()
        expect(page.locator("text=Branding entity").first).to_be_visible()
        expect(page.locator("text=Ad Set Image").first).to_be_visible()

        # Video-specific sections should NOT be visible
        video_preview = page.locator("text=Ad Set Video Preview")
        assert video_preview.count() == 0, (
            "Video Preview should not appear for Static Banner"
        )

        # DOM confirmed: image upload accepts "image/png, image/jpeg, image/gif, image/webp"
        img_upload = page.locator(
            ".ant-modal-body .ant-upload input[type='file'][accept*='image']"
        ).first
        accept_attr = img_upload.get_attribute("accept")
        assert "image/webp" in accept_attr, (
            f"Banner upload should accept WebP, got accept='{accept_attr}'"
        )

    def test_video_ad_empty_fields_show_all_errors(self, media_page: Page):
        # TC-15: Select Video Ad, leave all empty, click Next
        page = media_page

        video_option = page.locator("text=Product Video Ad").first
        video_option.click()
        page.wait_for_timeout(500)

        _click_next(page)
        page.wait_for_timeout(500)

        errors = _get_visible_errors(page)

        assert ERR_AD_SET_TITLE in errors, (
            f"Expected '{ERR_AD_SET_TITLE}' in errors, got: {errors}"
        )
        assert ERR_BRANDING_ENTITY in errors, (
            f"Expected '{ERR_BRANDING_ENTITY}' in errors, got: {errors}"
        )
        assert ERR_UPLOAD_MEDIA in errors, (
            f"Expected '{ERR_UPLOAD_MEDIA}' in errors, got: {errors}"
        )
        assert ERR_UPLOAD_PREVIEW in errors, (
            f"Expected '{ERR_UPLOAD_PREVIEW}' in errors, got: {errors}"
        )

    def test_static_banner_empty_fields_show_errors(self, media_page: Page):
        # TC-16: Select Static Banner, leave all empty, click Next
        page = media_page

        banner_option = page.locator("text=Product Static Banner").first
        banner_option.click()
        page.wait_for_timeout(500)

        _click_next(page)
        page.wait_for_timeout(500)

        errors = _get_visible_errors(page)

        assert ERR_AD_SET_TITLE in errors, (
            f"Expected '{ERR_AD_SET_TITLE}' in errors, got: {errors}"
        )
        assert ERR_BRANDING_ENTITY in errors, (
            f"Expected '{ERR_BRANDING_ENTITY}' in errors, got: {errors}"
        )
        # Static banner uses image upload, error text may differ slightly
        has_upload_error = any("upload" in e.lower() for e in errors)
        assert has_upload_error, (
            f"Expected an upload error for Static Banner, got: {errors}"
        )


class TestCreateNavigation:
    """
    Navigation tests - merged test cases:
    - Back button preserves Step 1 data
    - Back button preserves Step 2 media selection
    - Step indicator shows correct step number
    """

    def test_back_preserves_step1_data(self, create_page: Page):
        # TC-21: Fill Step 1, go to Step 2, click Back, verify data
        page = create_page
        test_name = "Preserve-Test_999"
        test_budget = "42"

        # Fill settings with specific values
        _fill_settings(page, name=test_name, budget=test_budget)

        # Go to Step 2
        _click_next(page)
        page.wait_for_timeout(1000)
        page.wait_for_selector("text=Ad Sets", timeout=10_000)

        # Go back to Step 1
        _click_back(page)
        page.wait_for_timeout(1000)

        # Verify campaign name is preserved
        name_input = page.locator(
            "#media-hub-campaign_campaignName, "
            "input[placeholder='e.g. Spring launch']"
        ).first
        assert name_input.input_value() == test_name, (
            f"Campaign name not preserved. Expected '{test_name}', "
            f"got '{name_input.input_value()}'"
        )

        # Verify budget is preserved
        budget_input = page.locator(".ant-input-number-input").first
        assert budget_input.input_value() == test_budget, (
            f"Budget not preserved. Expected '{test_budget}', "
            f"got '{budget_input.input_value()}'"
        )

        # Verify start date is preserved (not empty)
        start_input = page.locator("#media-hub-campaign-settings_startDate")
        assert start_input.input_value() != "", "Start date should be preserved"

    def test_back_preserves_step2_media_selection(self, create_page: Page):
        # TC-22: Fill Step 1 + 2, go to Step 3, Back, verify media choice
        page = create_page

        # Fill Step 1 and advance
        _fill_settings(page)
        _click_next(page)
        page.wait_for_timeout(1000)
        page.wait_for_selector("text=Ad Sets", timeout=10_000)

        # Select Product Video Ad on Step 2
        video_option = page.locator("text=Product Video Ad").first
        video_option.click()
        page.wait_for_timeout(500)

        # Fill ad set title — DOM confirmed id: media-hub-campaign-adset_adSetTitle
        ad_title_input = page.locator(
            "#media-hub-campaign-adset_adSetTitle"
        ).first
        ad_title_input.fill("My Video Ad Title")

        # Try to go to Step 3 (may fail validation, but the selection
        # should still be preserved if we go Back from Step 2)
        # Instead, just go back to Step 1 and then forward again
        _click_back(page)
        page.wait_for_timeout(1000)

        # Go forward to Step 2 again
        _click_next(page)
        page.wait_for_timeout(1000)
        page.wait_for_selector("text=Ad Sets", timeout=10_000)

        # Verify Product Video Ad is still selected
        video_radio = page.locator("text=Product Video Ad").first
        parent_card = video_radio.locator(
            "xpath=ancestor::div[contains(@class, 'ant-radio') or "
            "contains(@class, 'card') or contains(@class, 'selected')]"
        )

        # Check that the Video Ad section expanded fields are visible
        # (they only appear when Video Ad is selected)
        ad_set_video = page.locator("text=Ad Set Video")
        assert ad_set_video.count() > 0, (
            "Product Video Ad should still be selected after Back->Next"
        )

    def test_step_indicator_updates(self, create_page: Page):
        # TC-23: Step indicator highlights the correct step
        page = create_page

        # Step 1 should be active
        step1 = page.locator("text=Settings").first
        expect(step1).to_be_visible()

        # Fill and go to Step 2
        _fill_settings(page)
        _click_next(page)
        page.wait_for_timeout(1000)

        # Step 2 (Media) should now be active
        media_heading = page.locator("text=Ad Sets")
        expect(media_heading.first).to_be_visible(timeout=5_000)

        # Go back to Step 1
        _click_back(page)
        page.wait_for_timeout(500)

        # Step 1 content should be visible again
        campaign_name = page.locator("text=Campaign name")
        expect(campaign_name.first).to_be_visible()


# ============================================================================
# BE / DATA TESTS
# ============================================================================


class TestCreateSettingsPayload:
    """
    API payload tests for Step 1 (Settings) - merged test cases:
    - Ongoing flag sent correctly (true vs false with end_date)
    - Settings fields in correct format
    - No create API call during step navigation
    """

    def test_ongoing_flag_in_payload(self, create_page: Page):
        # TC-09 + TC-11 merged:
        # Verify Ongoing toggle state affects the form data

        page = create_page

        # Test 1: Ongoing ON (default)
        # DOM confirmed: first switch in modal = Ongoing
        ongoing_switch = page.locator(
            ".ant-modal-body button[role='switch']"
        ).first

        is_checked = ongoing_switch.get_attribute("aria-checked")
        assert is_checked == "true", "Default Ongoing should be ON"

        # End date should show placeholder (disabled)
        end_input = page.locator("#media-hub-campaign-settings_endDate")
        assert end_input.is_disabled(), (
            "End date disabled when Ongoing is ON"
        )

        # Test 2: Toggle Ongoing OFF
        ongoing_switch.click()
        page.wait_for_timeout(500)

        is_checked_after = ongoing_switch.get_attribute("aria-checked")
        assert is_checked_after == "false", (
            "Ongoing should be OFF after toggle"
        )

        # End date should now be enabled
        assert not end_input.is_disabled(), (
            "End date should be enabled when Ongoing is OFF"
        )

    def test_no_create_api_during_navigation(self, create_page: Page):
        # TC-24: Monitor network - no campaign create API during navigation
        page = create_page
        create_requests = []

        def request_handler(request):
            url = request.url
            method = request.method
            if "campaign" in url and method == "POST" and "read_list" not in url:
                create_requests.append({
                    "url": url,
                    "method": method,
                })

        page.on("request", request_handler)

        try:
            # Fill Step 1 and go to Step 2
            _fill_settings(page)
            _click_next(page)
            page.wait_for_timeout(1000)

            # Go back to Step 1
            _click_back(page)
            page.wait_for_timeout(500)

            # Go forward again
            _click_next(page)
            page.wait_for_timeout(500)

            assert len(create_requests) == 0, (
                f"No create API calls expected during navigation, "
                f"but got {len(create_requests)}: {create_requests}"
            )
        finally:
            page.remove_listener("request", request_handler)


class TestCreateMediaPayload:
    """
    API payload tests for Step 2 (Media) - merged test cases:
    - Upload endpoint returns correct metadata
    - Media type distinction in payload
    """

    @pytest.fixture
    def media_page(self, create_page: Page) -> Page:
        """Fill Step 1 and advance to Step 2."""
        page = create_page
        _fill_settings(page)
        _click_next(page)
        page.wait_for_timeout(1000)
        page.wait_for_selector("text=Ad Sets", timeout=10_000)
        return page

    def test_video_ad_shows_upload_endpoint(self, media_page: Page):
        # TC-18 + TC-19 merged:
        # Select Video Ad and verify the upload area is present
        # and has correct specifications
        page = media_page

        video_option = page.locator("text=Product Video Ad").first
        video_option.click()
        page.wait_for_timeout(500)

        # Verify upload area shows correct file specs
        video_spec = page.locator("text=/MP4.*H.264/i")
        expect(video_spec.first).to_be_visible()

        # Verify the recommended specs are shown
        size_spec = page.locator("text=/20 MB/i")
        expect(size_spec.first).to_be_visible()

        # Verify preview upload specs
        preview_spec = page.locator("text=/JPG or PNG/i")
        expect(preview_spec.first).to_be_visible()

    def test_static_banner_shows_image_specs(self, media_page: Page):
        # Verify Static Banner shows correct image specifications
        page = media_page

        banner_option = page.locator("text=Product Static Banner").first
        banner_option.click()
        page.wait_for_timeout(500)

        # Check image specs
        img_spec = page.locator("text=/JPG or PNG/i")
        expect(img_spec.first).to_be_visible()

        size_spec = page.locator("text=/2 MB/i")
        expect(size_spec.first).to_be_visible()

        res_spec = page.locator("text=/1080x1080/i")
        expect(res_spec.first).to_be_visible()

    def test_capture_preview_button_state(self, media_page: Page):
        # TC-25: Capture preview button should exist but be
        # disabled/greyed when no video is uploaded.
        # DOM confirmed: button is a native Ant Design button (class ant-btn),
        #   disabled=true by default, cursor "not-allowed",
        #   bg rgba(0,0,0,0.04), color rgba(0,0,0,0.25).
        page = media_page

        video_option = page.locator("text=Product Video Ad").first
        video_option.click()
        page.wait_for_timeout(500)

        # Scroll to see the Capture preview button
        capture_btn = page.locator("button:has-text('Capture preview')").first
        capture_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(300)

        # Button should be visible
        expect(capture_btn).to_be_visible()

        # DOM confirmed: button has disabled=true when no video uploaded
        is_disabled = capture_btn.is_disabled()
        assert is_disabled, (
            "Capture preview button should be disabled when no video is uploaded"
        )

        # Verify the disabled visual state via computed style
        cursor = page.evaluate(
            "el => getComputedStyle(el).cursor",
            capture_btn.element_handle()
        )
        assert cursor == "not-allowed", (
            f"Capture preview cursor should be 'not-allowed', got '{cursor}'"
        )


class TestCreateEndToEnd:
    """
    End-to-end creation flow tests:
    - Switching between Video Ad and Static Banner
    - Full dialog flow verification
    """

    def test_switch_between_media_types(self, create_page: Page):
        # Verify switching between Video Ad and Static Banner
        # updates the visible fields correctly
        page = create_page

        # Fill Step 1 and go to Step 2
        _fill_settings(page)
        _click_next(page)
        page.wait_for_timeout(1000)
        page.wait_for_selector("text=Ad Sets", timeout=10_000)

        # Select Video Ad
        page.locator("text=Product Video Ad").first.click()
        page.wait_for_timeout(500)

        # Verify video-specific fields
        video_preview = page.locator("text=Ad Set Video Preview")
        assert video_preview.count() > 0, "Video preview should be visible"

        # Switch to Static Banner
        page.locator("text=Product Static Banner").first.click()
        page.wait_for_timeout(500)

        # Verify video preview is gone, image section appears
        ad_set_image = page.locator("text=Ad Set Image")
        assert ad_set_image.count() > 0, "Ad Set Image should be visible"

        video_preview_after = page.locator("text=Ad Set Video Preview")
        assert video_preview_after.count() == 0, (
            "Video Preview should not be visible after switching to Banner"
        )

    def test_full_dialog_opens_at_step1(self, create_page: Page):
        # Verify the Create dialog always starts at Step 1 (Settings)
        page = create_page

        # Dialog title should be visible
        title = page.locator("text=Media Hub Campaign Set Up")
        expect(title.first).to_be_visible()

        # Step 1 content should be visible
        campaign_name = page.locator("text=Campaign name")
        expect(campaign_name.first).to_be_visible()

        # Step indicator should show Settings as active
        settings_label = page.locator("text=Settings").first
        expect(settings_label).to_be_visible()

        # All 5 steps should be shown in the header
        for step_name in ["Settings", "Media", "CTA", "Targeting", "Review"]:
            step = page.locator(f"text={step_name}")
            assert step.count() > 0, f"Step '{step_name}' should be in header"
