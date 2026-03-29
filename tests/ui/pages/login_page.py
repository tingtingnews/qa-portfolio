from playwright.sync_api import Page
from .base_page import BasePage

class LoginPage(BasePage):
    USERNAME_INPUT = "#user-name"
    PASSWORD_INPUT = "#password"
    LOGIN_BUTTON   = "#login-button"
    ERROR_MESSAGE  = "[data-test='error']"

    def __init__(self, page: Page):
        super().__init__(page)

    def goto(self):
        self.navigate("https://www.saucedemo.com")

    def login(self, username: str, password: str):
        self.page.fill(self.USERNAME_INPUT, username)
        self.page.fill(self.PASSWORD_INPUT, password)
        self.page.click(self.LOGIN_BUTTON)

    def get_error_message(self) -> str:
        return self.page.inner_text(self.ERROR_MESSAGE)

    def is_error_visible(self) -> bool:
        return self.page.is_visible(self.ERROR_MESSAGE)
