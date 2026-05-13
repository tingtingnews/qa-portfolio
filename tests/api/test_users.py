import pytest
import requests

# Using JSONPlaceholder - 100% free, no API key, no rate limits
# https://jsonplaceholder.typicode.com

@pytest.mark.api
class TestUsers:

    def test_get_users_returns_200(self, api_base_url):
        r = requests.get(f"{api_base_url}/users")
        assert r.status_code == 200

    def test_get_users_returns_list(self, api_base_url):
        r = requests.get(f"{api_base_url}/users")
        body = r.json()
        assert isinstance(body, list)
        assert len(body) > 0

    def test_get_single_user_returns_200(self, api_base_url):
        r = requests.get(f"{api_base_url}/users/1")
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_get_nonexistent_user_returns_404(self, api_base_url):
        r = requests.get(f"{api_base_url}/users/9999")
        assert r.status_code == 404

    def test_create_user_returns_201(self, api_base_url):
        payload = {"name": "Ting", "username": "ting_qa", "email": "ting@qa.com"}
        r = requests.post(f"{api_base_url}/users", json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Ting"
        assert "id" in body

    def test_update_user_returns_200(self, api_base_url):
        payload = {"name": "Ting Updated", "email": "ting_updated@qa.com"}
        r = requests.put(f"{api_base_url}/users/1", json=payload)
        assert r.status_code == 200
        assert r.json()["name"] == "Ting Updated"

    def test_patch_user_returns_200(self, api_base_url):
        r = requests.patch(f"{api_base_url}/users/1", json={"name": "Ting Patched"})
        assert r.status_code == 200
        assert r.json()["name"] == "Ting Patched"

    def test_delete_user_returns_200(self, api_base_url):
        r = requests.delete(f"{api_base_url}/users/1")
        assert r.status_code == 200

    def test_response_has_expected_fields(self, api_base_url):
        r = requests.get(f"{api_base_url}/users/1")
        body = r.json()
        for field in ["id", "name", "username", "email"]:
            assert field in body, f"Missing field: {field}"

    def test_response_time_under_2s(self, api_base_url):
        r = requests.get(f"{api_base_url}/users")
        assert r.elapsed.total_seconds() < 2.0

    @pytest.mark.parametrize("user_id", [1, 2, 3, 5, 10])
    def test_multiple_users_exist(self, api_base_url, user_id):
        r = requests.get(f"{api_base_url}/users/{user_id}")
        assert r.status_code == 200
        assert r.json()["id"] == user_id
