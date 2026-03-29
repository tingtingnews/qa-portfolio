from playwright.sync_api import Page
from .base_page import BasePage

class InventoryPage(BasePage):
    TITLE           = ".title"
    CART_BADGE      = ".shopping_cart_badge"
    CART_LINK       = ".shopping_cart_link"
    ADD_TO_CART_BTN = "button[data-test^='add-to-cart']"
    SORT_DROPDOWN   = "[data-test='product_sort_container']"

    def __init__(self, page: Page):
        super().__init__(page)

    def is_loaded(self) -> bool:
        return self.page.is_visible(self.TITLE)

    def add_first_item_to_cart(self):
        self.page.locator(self.ADD_TO_CART_BTN).first.click()

    def get_cart_count(self) -> int:
        if self.page.is_visible(self.CART_BADGE):
            return int(self.page.inner_text(self.CART_BADGE))
        return 0

    def go_to_cart(self):
        self.page.click(self.CART_LINK)

    def sort_by(self, option: str):
        self.page.select_option(self.SORT_DROPDOWN, option)
