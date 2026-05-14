"""
conftest.py — Playwright fixtures for Shping Admin UI tests.

Auth strategy — why storage_state alone does NOT work here:
    The Shping admin is a React/Redux SPA.  When a user logs in, the login
    action dispatches Redux thunks that bootstrap participant data, brand
    lists, and widget subscriptions.  storage_state restores
    cookies + localStorage but NOT the in-memory Redux store, so those
    thunks never run and the analytics widgets never render.

    The only reliable approach is a real browser login.  To keep the suite
    fast, we create ONE browser + ONE context + ONE page for the entire
    pytest session (session-scoped).  The page logs in once and stays alive;
    each test navigates on it.

Setup:
    pip install pytest playwright pytest-playwright
    playwright install chromium

Credentials (override via env vars):
    export SHPING_ADMIN_EMAIL="hsiangjung.ting@gmail.com"
    export SHPING_ADMIN_PASSWORD="Testingting123#"

Run:
    pytest test_analytics_overview.py -v --headed
    pytest test_analytics_overview.py -v --headed --slowmo=500
"""

import os
import re
import pytest
from playwright.sync_api import Page, Playwright

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL           = os.getenv("SHPING_BASE_URL", "https://dev-admin.shping.com")
API_BASE_URL       = "https://dev-api.shping.com"
LOGIN_URL          = BASE_URL
ANALYTICS_PERF_URL     = f"{BASE_URL}/admin/analytics/overview"   # "Performance" tab
ANALYTICS_ROI_URL      = f"{BASE_URL}/admin/analytics/roi"       # "Overview" tab
ANALYTICS_AUDIENCE_URL = f"{BASE_URL}/admin/analytics/audience"  # "Audience" tab
ANALYTICS_CONVERSION_URL = f"{BASE_URL}/admin/analytics/conversion"  # "Conversion" tab
ANALYTICS_SPEND_URL      = f"{BASE_URL}/admin/analytics/spend"       # "Spend" tab
ANALYTICS_INSIGHTS_URL   = f"{BASE_URL}/admin/analytics/insights"    # "Insights" tab
CONTRIBUTORS_URL         = f"{BASE_URL}/admin/contributors"          # Contributors page
CAMPAIGNS_URL            = f"{BASE_URL}/admin/media-hub/campaigns"   # Campaigns page

# Credentials loaded from environment variables only.
# - Locally:  export SHPING_ADMIN_EMAIL="..." and SHPING_ADMIN_PASSWORD="..."
# - CI/CD:    stored in GitHub Secrets, injected automatically by the workflow
# - NEVER hardcode credentials in source code.
ADMIN_EMAIL    = os.getenv("SHPING_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("SHPING_ADMIN_PASSWORD")

if not ADMIN_EMAIL or not ADMIN_PASSWORD:
    raise RuntimeError(
        "Missing credentials. Set SHPING_ADMIN_EMAIL and SHPING_ADMIN_PASSWORD "
        "as environment variables before running tests."
    )


# ── Session-scoped: one browser login, shared for all tests ───────────────────

@pytest.fixture(scope="session")
def session_page(playwright: Playwright, request) -> Page:
    """
    Creates ONE browser + context + page for the entire test session.

    - Performs a full interactive login so the React/Redux app initialises
      correctly (participant data, brands, widget subscriptions, etc.)
    - The page stays open for the whole session; tests navigate on it.
    - Respects --headed / --headless flags passed to pytest.
    """
    headed = request.config.getoption("--headed", default=False)
    browser = playwright.chromium.launch(
        headless=not headed,
        slow_mo=100 if headed else 0,
    )
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="en-US",
    )
    page = context.new_page()

    # Full interactive login
    page.goto(LOGIN_URL)
    page.wait_for_load_state("networkidle")
    page.get_by_role("textbox", name="you@domain.com").fill(ADMIN_EMAIL)
    page.get_by_role("textbox", name="Your password").fill(ADMIN_PASSWORD)
    page.get_by_role("button", name="Login").click()
    page.wait_for_url(lambda url: "/admin" in url, timeout=25_000)
    page.wait_for_load_state("networkidle")

    # Switch to the correct participant context.
    # After login the app lands on the personal "Gigi" account — analytics
    # data lives under "Authenticateit Pty Ltd", so we must switch before
    # navigating to any analytics page.
    #
    # Why this approach:
    #   1. wait_for_selector("text=Gigi") — ensures the participant widget
    #      has fully rendered before we try to interact with it.
    #   2. wait_for_timeout(500) after opening — the Ant Design Select
    #      dropdown has an open animation; without this pause the next
    #      click fires before the option list is visible.
    #   3. Scope the option click to [role="option"] inside the visible
    #      .ant-select-dropdown — avoids accidentally clicking an element
    #      with the same text that may already exist elsewhere on the page.
    #   4. Verify the switch with wait_for_selector — confirms the header
    #      now shows "Authenticateit Pty Ltd" before any test runs.
    # Open the participant dropdown using the codegen-verified selector.
    # The switcher element has title="Gigi" and contains a combobox inside it.
    page.get_by_title("Gigi").get_by_role("combobox").click()
    page.wait_for_timeout(1000)

    # Use JavaScript to click the option directly — all Playwright selectors
    # (get_by_role("option"), get_by_text, locator(".ant-select-dropdown ..."))
    # have failed because Ant Design renders the dropdown in a portal outside
    # the main DOM tree and the option elements may not have [role="option"]
    # at the point Playwright queries for them.
    #
    # DevTools inspection confirmed the option content elements have class
    # "ant-select-item-option-content".  We find the one whose text includes
    # "Authenticateit" and click it via evaluate() which runs synchronously
    # in the page's JS context and bypasses all selector-timing issues.
    page.evaluate("""
        const items = document.querySelectorAll('.ant-select-item-option-content');
        const target = Array.from(items).find(el => el.textContent.includes('Authenticateit'));
        if (target) { target.click(); }
        else { throw new Error('Authenticateit option not found in dropdown'); }
    """)

    # Confirm the switcher now shows the new participant before any test runs.
    # The DevTools DOM shows the selected value lives in:
    #   div.ant-select-content[title="Authenticateit Pty Ltd"]
    page.wait_for_selector(
        ".ant-select-content[title*='Authenticateit']", timeout=10_000
    )
    page.wait_for_load_state("networkidle")

    yield page

    page.close()
    context.close()
    browser.close()


# ── analytics_page: navigate to the Performance tab, wait for widget content ──

@pytest.fixture
def analytics_page(session_page: Page) -> Page:
    """
    Navigates the shared session page to Analytics > Performance and waits
    until the 'Reach' widget heading is visible — confirming the full page
    including widget data has rendered.

    We do NOT use wait_for_load_state("networkidle") here because the app
    has background polling / long-lived connections that prevent it from
    ever reaching networkidle.  The Reach heading appearing is the reliable
    signal that the page and its widgets are ready.
    """
    session_page.goto(ANALYTICS_PERF_URL)
    try:
        session_page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass   # background polling prevents networkidle — that's expected
    session_page.wait_for_selector("h3:has-text('Reach')", timeout=30_000)

    # Why this reset exists:
    # The app saves the last-used date range in localStorage.  When goto()
    # reloads the page, it silently restores whatever range was last used —
    # often FULL_RANGE from a previous test.  If a test then calls
    # set_date_range(FULL_RANGE), the dates haven't changed, so the app
    # fires no new GraphQL requests, and capture_responses() returns [].
    #
    # Resetting to a single-day range (Apr 4 only) guarantees that every
    # subsequent set_date_range(FULL_RANGE) is a real date change, always
    # triggers new network requests, and lets capture_responses() work.
    try:
        inputs = session_page.locator("input")
        date_inputs = [
            inputs.nth(i)
            for i in range(min(inputs.count(), 20))
            if re.match(r"\d{2}/\d{2}/\d{4}", inputs.nth(i).input_value())
        ]
        if len(date_inputs) >= 2:
            for inp, val in zip(date_inputs[:2], ["04/04/2026", "04/04/2026"]):
                inp.click(click_count=3)
                inp.type(val)
                session_page.keyboard.press("Tab")
            session_page.keyboard.press("Enter")
            # Wait for the reset request to fully complete so the response
            # does not leak into the next test's capture_responses window.
            try:
                session_page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass
            session_page.wait_for_timeout(2000)
    except Exception:
        pass   # reset is best-effort — tests will handle if it didn't work

    return session_page


# ── page: shared session page for tests that manage their own navigation ──────

@pytest.fixture
def page(session_page: Page) -> Page:
    """
    Returns the shared session page for tests that do their own navigation
    (e.g. API health tests that need to set up listeners before goto).
    """
    return session_page


# ── audience_page: navigate to Analytics > Audience, set date range ───────────

@pytest.fixture
def audience_page(session_page: Page) -> Page:
    """
    Navigates the shared session page to Analytics > Audience and waits
    until the 'Audience' widget heading is visible.

    Sets the date range to 03/01/2026 – 04/07/2026 so every test in
    TestAudienceCharts sees the same data window.
    """
    session_page.goto(ANALYTICS_AUDIENCE_URL)
    try:
        session_page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass   # background polling prevents networkidle — expected

    # Wait for the first chart widget title to confirm page is ready
    session_page.wait_for_selector("text=Audience", timeout=30_000)

    # Set date range to 03/01/2026 – 04/07/2026
    inputs = session_page.locator("input")
    date_inputs = [
        inputs.nth(i)
        for i in range(min(inputs.count(), 20))
        if re.match(r"\d{2}/\d{2}/\d{4}", inputs.nth(i).input_value())
    ]
    if len(date_inputs) >= 2:
        for inp, val in zip(date_inputs[:2], ["03/01/2026", "04/07/2026"]):
            inp.click(click_count=3)
            inp.type(val)
            session_page.keyboard.press("Tab")
        session_page.keyboard.press("Enter")
        session_page.wait_for_timeout(2000)

    return session_page


# ── conversion_page: navigate to Analytics > Conversion, set date range ─────

@pytest.fixture
def conversion_page(session_page: Page) -> Page:
    """
    Navigates the shared session page to Analytics > Conversion and waits
    until the 'Receipts with Booster' widget heading is visible.

    Sets the date range to 03/01/2026 – 04/07/2026 so every test in
    TestConversionSummaryWidgets sees the same data window.
    """
    session_page.goto(ANALYTICS_CONVERSION_URL)
    try:
        session_page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass   # background polling prevents networkidle — expected

    # Wait for the first summary widget to confirm page is ready
    session_page.wait_for_selector("text=Receipts with Booster", timeout=30_000)

    # Set date range to 03/01/2026 – 04/07/2026
    inputs = session_page.locator("input")
    date_inputs = [
        inputs.nth(i)
        for i in range(min(inputs.count(), 20))
        if re.match(r"\d{2}/\d{2}/\d{4}", inputs.nth(i).input_value())
    ]
    if len(date_inputs) >= 2:
        for inp, val in zip(date_inputs[:2], ["03/01/2026", "04/07/2026"]):
            inp.click(click_count=3)
            inp.type(val)
            session_page.keyboard.press("Tab")
        session_page.keyboard.press("Enter")
        session_page.wait_for_timeout(2000)

    return session_page


# ── spend_page: navigate to Analytics > Spend, set date range ────────────────

@pytest.fixture
def spend_page(session_page: Page) -> Page:
    """
    Navigates the shared session page to Analytics > Spend and waits
    until the 'Interaction clicks' widget heading is visible.

    Sets the date range to 03/01/2026 – 04/07/2026 so every test in
    TestSpendSummaryWidgets sees the same data window.
    """
    session_page.goto(ANALYTICS_SPEND_URL)
    try:
        session_page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass   # background polling prevents networkidle — expected

    # Wait for the first metric widget to confirm page is ready
    session_page.wait_for_selector("text=Interaction clicks", timeout=30_000)

    # Set date range to 03/01/2026 – 04/07/2026
    inputs = session_page.locator("input")
    date_inputs = [
        inputs.nth(i)
        for i in range(min(inputs.count(), 20))
        if re.match(r"\d{2}/\d{2}/\d{4}", inputs.nth(i).input_value())
    ]
    if len(date_inputs) >= 2:
        for inp, val in zip(date_inputs[:2], ["03/01/2026", "04/07/2026"]):
            inp.click(click_count=3)
            inp.type(val)
            session_page.keyboard.press("Tab")
        session_page.keyboard.press("Enter")
        session_page.wait_for_timeout(2000)

    return session_page


# ── insights_page: navigate to Analytics > Insights, set date range ──────────

@pytest.fixture
def insights_page(session_page: Page) -> Page:
    """
    Navigates the shared session page to Analytics > Insights and waits
    until the 'Retailer Mix' widget heading is visible.

    Sets the date range to 03/01/2026 – 04/07/2026 so every test in
    TestInsightsCharts and TestInsightsTables sees the same data window.
    """
    session_page.goto(ANALYTICS_INSIGHTS_URL)
    try:
        session_page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception:
        pass   # background polling prevents networkidle — expected

    # Wait for the first chart widget to confirm page is ready
    session_page.wait_for_selector("text=Retailer Mix", timeout=30_000)

    # Set date range to 03/01/2026 – 04/07/2026
    inputs = session_page.locator("input")
    date_inputs = [
        inputs.nth(i)
        for i in range(min(inputs.count(), 20))
        if re.match(r"\d{2}/\d{2}/\d{4}", inputs.nth(i).input_value())
    ]
    if len(date_inputs) >= 2:
        for inp, val in zip(date_inputs[:2], ["03/01/2026", "04/07/2026"]):
            inp.click(click_count=3)
            inp.type(val)
            session_page.keyboard.press("Tab")
        session_page.keyboard.press("Enter")
        session_page.wait_for_timeout(2000)

    return session_page


# ── contributors_page: navigate to Contributors, wait for list to render ──────

@pytest.fixture
def contributors_page(session_page: Page) -> Page:
    """
    Navigates the shared session page to the Contributors list and waits
    until the results summary text (e.g. "X contributions are found") is
    visible — confirming the page and its data have fully loaded.
    """
    session_page.goto(CONTRIBUTORS_URL)
    try:
        session_page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        pass   # background polling prevents networkidle — expected

    # Wait for the results count text that confirms data has loaded.
    session_page.wait_for_selector("text=contributions are found", timeout=30_000)
    return session_page


# ── unauth_page: fresh unauthenticated context for login-flow tests ───────────

@pytest.fixture
def unauth_page(playwright: Playwright, request) -> Page:
    """
    Spawns a brand-new browser context with no session — used only by the
    login-flow tests that need to test authentication from scratch.
    """
    headed = request.config.getoption("--headed", default=False)
    browser = playwright.chromium.launch(
        headless=not headed,
        slow_mo=100 if headed else 0,
    )
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="en-US",
    )
    page = context.new_page()

    yield page

    page.close()
    context.close()
    browser.close()