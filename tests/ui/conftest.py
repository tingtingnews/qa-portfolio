import pytest
from playwright.sync_api import Page

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

@pytest.fixture(autouse=True)
def screenshot_on_failure(request, page: Page):
    yield
    rep = getattr(request.node, "rep_call", None)
    if rep and rep.failed:
        page.screenshot(path=f"reports/FAIL_{request.node.name}.png")
