import pytest
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.inventory_page import InventoryPage

@pytest.mark.ui
class TestCart:

    @pytest.fixture(autouse=True)
    def login_first(self, page, credentials):
        login = LoginPage(page)
        login.goto()
        login.login(credentials["standard"]["username"], credentials["standard"]["password"])

    def test_add_item_increments_cart_badge(self, page):
        inv = InventoryPage(page)
        assert inv.get_cart_count() == 0
        inv.add_first_item_to_cart()
        assert inv.get_cart_count() == 1

    def test_cart_badge_hidden_when_empty(self, page):
        assert InventoryPage(page).get_cart_count() == 0
