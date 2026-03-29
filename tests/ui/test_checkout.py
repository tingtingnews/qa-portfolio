import pytest
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.inventory_page import InventoryPage
from tests.ui.pages.checkout_page import CheckoutPage

@pytest.mark.ui
class TestCheckout:

    @pytest.fixture(autouse=True)
    def add_item_to_cart(self, page, credentials):
        login = LoginPage(page)
        login.goto()
        login.login(credentials["standard"]["username"], credentials["standard"]["password"])
        inv = InventoryPage(page)
        inv.add_first_item_to_cart()
        inv.go_to_cart()

    def test_full_checkout_happy_path(self, page):
        checkout = CheckoutPage(page)
        checkout.proceed_to_checkout()
        checkout.fill_info("Ting", "Tester", "10001")
        checkout.continue_checkout()
        checkout.finish()
        assert checkout.is_order_complete()

    def test_checkout_missing_first_name(self, page):
        checkout = CheckoutPage(page)
        checkout.proceed_to_checkout()
        checkout.fill_info("", "Tester", "10001")
        checkout.continue_checkout()
        assert "first name is required" in checkout.get_error_message().lower()
