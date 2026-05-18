import pytest
import os

class TestZerodhaAuth:
    def test_auth_initializes_in_paper_mode(self, auth):
        assert auth.paper_trade is True
        assert auth.kite is None

    def test_get_login_url_paper_trade(self, auth):
        url = auth.get_login_url()
        assert isinstance(url, str)
        assert len(url) > 0
        assert "zerodha" in url.lower() or "mock" in url.lower()

    def test_generate_session_paper_trade(self, auth):
        result = auth.generate_session("mock_request_token_123")
        assert "access_token" in result
        assert result["paper_trade"] is True
        assert result["access_token"].startswith("mock_access_token_")

    def test_is_authenticated_after_session(self, auth):
        assert not auth.is_authenticated()
        auth.generate_session("mock_token_abc")
        assert auth.is_authenticated()

    def test_get_access_token(self, auth):
        auth.generate_session("mock_token_xyz")
        token = auth.get_access_token()
        assert token is not None
        assert len(token) > 5

    def test_save_and_load_session(self, auth, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        auth.generate_session("test_token_save")
        new_auth = type(auth)(paper_trade=True)
        result = new_auth.load_existing_session()
        assert result is True
        assert new_auth.is_authenticated()

    def test_load_session_no_file(self, auth, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = auth.load_existing_session()
        assert result is False


class TestAuthAPI:
    def test_get_login_url_endpoint(self, client):
        response = client.get("/auth/login-url")
        assert response.status_code == 200
        data = response.json()
        assert "login_url" in data
        assert isinstance(data["login_url"], str)

    def test_auth_status_unauthenticated(self, client):
        response = client.get("/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert "authenticated" in data
        assert "paper_trade" in data

    def test_create_session_endpoint(self, client):
        response = client.post("/auth/session", json={"request_token": "mock_token_test"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data

    def test_auth_status_after_login(self, client):
        client.post("/auth/session", json={"request_token": "mock_token_status"})
        response = client.get("/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
