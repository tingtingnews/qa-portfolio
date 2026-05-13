import pytest
import requests

# JSONPlaceholder posts endpoint — testing as "auth-like" resource
# Real auth testing will come when you use a project with actual auth

@pytest.mark.api
class TestPosts:
    """
    JSONPlaceholder doesn't have auth, so this tests Posts CRUD.
    In a real project, this file would test login/logout/token flows.
    """

    def test_get_all_posts_returns_200(self, api_base_url):
        r = requests.get(f"{api_base_url}/posts")
        assert r.status_code == 200
        assert len(r.json()) == 100  # JSONPlaceholder always has 100 posts

    def test_create_post_returns_201(self, api_base_url):
        payload = {"title": "QA Test Post", "body": "Testing API automation", "userId": 1}
        r = requests.post(f"{api_base_url}/posts", json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "QA Test Post"
        assert "id" in body

    def test_get_posts_by_user(self, api_base_url):
        r = requests.get(f"{api_base_url}/posts?userId=1")
        assert r.status_code == 200
        posts = r.json()
        assert len(posts) > 0
        assert all(p["userId"] == 1 for p in posts)

    def test_missing_required_fields_still_creates(self, api_base_url):
        # JSONPlaceholder is forgiving — good to document this behaviour
        r = requests.post(f"{api_base_url}/posts", json={})
        assert r.status_code == 201

    def test_content_type_is_json(self, api_base_url):
        r = requests.get(f"{api_base_url}/posts/1")
        assert "application/json" in r.headers["Content-Type"]
