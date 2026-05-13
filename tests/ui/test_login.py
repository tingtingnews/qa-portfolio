import pytest
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.inventory_page import InventoryPage

@pytest.mark.ui
class TestLogin:

    def test_valid_login(self, page, credentials):
        login = LoginPage(page)
        login.goto()
        login.login(credentials["standard"]["username"], credentials["standard"]["password"])
        assert InventoryPage(page).is_loaded()

    def test_locked_user_sees_error(self, page, credentials):
        login = LoginPage(page)
        login.goto()
        login.login(credentials["locked"]["username"], credentials["locked"]["password"])
        assert login.is_error_visible()
        assert "locked out" in login.get_error_message().lower()

    def test_empty_username_shows_error(self, page, credentials):
        login = LoginPage(page)
        login.goto()
        login.login("", credentials["standard"]["password"])
        assert "username is required" in login.get_error_message().lower()

    def test_empty_password_shows_error(self, page, credentials):
        login = LoginPage(page)
        login.goto()
        login.login(credentials["standard"]["username"], "")
        assert "password is required" in login.get_error_message().lower()

    def test_wrong_password_shows_error(self, page, credentials):
        login = LoginPage(page)
        login.goto()
        login.login(credentials["standard"]["username"], "wrongpassword")
        assert login.is_error_visible()
