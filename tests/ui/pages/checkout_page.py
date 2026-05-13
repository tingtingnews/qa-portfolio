from playwright.sync_api import Page
from .base_page import BasePage

class CheckoutPage(BasePage):
    CHECKOUT_BTN    = "[data-test='checkout']"
    FIRST_NAME      = "[data-test='firstName']"
    LAST_NAME       = "[data-test='lastName']"
    POSTAL_CODE     = "[data-test='postalCode']"
    CONTINUE_BTN    = "[data-test='continue']"
    FINISH_BTN      = "[data-test='finish']"
    COMPLETE_HEADER = ".complete-header"
    ERROR_MESSAGE   = "[data-test='error']"

    def __init__(self, page: Page):
        super().__init__(page)

    def proceed_to_checkout(self):
        self.page.click(self.CHECKOUT_BTN)

    def fill_info(self, first: str, last: str, postal: str):
        self.page.fill(self.FIRST_NAME, first)
        self.page.fill(self.LAST_NAME, last)
        self.page.fill(self.POSTAL_CODE, postal)

    def continue_checkout(self):
        self.page.click(self.CONTINUE_BTN)

    def finish(self):
        self.page.click(self.FINISH_BTN)

    def is_order_complete(self) -> bool:
        return self.page.is_visible(self.COMPLETE_HEADER)

    def get_error_message(self) -> str:
        return self.page.inner_text(self.ERROR_MESSAGE)
