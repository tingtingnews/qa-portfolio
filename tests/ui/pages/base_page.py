from playwright.sync_api import Page

class BasePage:
    """All page objects inherit from this. Shared helpers live here."""

    def __init__(self, page: Page):
        self.page = page

    def navigate(self, url: str):
        self.page.goto(url)

    def get_title(self) -> str:
        return self.page.title()

    def wait_for_url(self, url_pattern: str):
        self.page.wait_for_url(url_pattern)

    def take_screenshot(self, name: str):
        self.page.screenshot(path=f"reports/{name}.png")
