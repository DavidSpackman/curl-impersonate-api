"""
Tests for curl-impersonate-api.

Unit tests use Flask's test client with mocked subprocess — no container needed.
Integration tests hit a live service at http://localhost:5555 — requires running container.

Run unit tests only:
    pip install pytest flask
    pytest test_app.py -v -m "not integration"

Run all tests (container must be running):
    pytest test_app.py -v
"""

import json
import pytest
from unittest.mock import patch, MagicMock

# ── Unit tests ────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Flask test client with wrappers mocked as available."""
    with patch("shutil.which", side_effect=lambda w: f"/usr/bin/{w}"):
        import importlib
        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        with app_module.app.test_client() as c:
            yield c, app_module


class TestHealth:
    def test_returns_ok(self, client):
        c, _ = client
        r = c.get("/health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "ok"

    def test_has_default_wrapper(self, client):
        c, _ = client
        data = c.get("/health").get_json()
        assert data["default_wrapper"] is not None
        assert data["default_wrapper"].startswith("curl_chrome")

    def test_default_is_highest_chrome(self, client):
        c, _ = client
        data = c.get("/health").get_json()
        # curl_chrome145 should be the highest available non-android chrome
        assert data["default_wrapper"] == "curl_chrome145"

    def test_available_wrappers_is_list(self, client):
        c, _ = client
        data = c.get("/health").get_json()
        assert isinstance(data["available_wrappers"], list)
        assert len(data["available_wrappers"]) > 0


class TestWrappers:
    def test_returns_available_and_all_known(self, client):
        c, _ = client
        r = c.get("/wrappers")
        assert r.status_code == 200
        data = r.get_json()
        assert "available" in data
        assert "all_known" in data

    def test_available_is_subset_of_all_known(self, client):
        c, _ = client
        data = c.get("/wrappers").get_json()
        assert set(data["available"]).issubset(set(data["all_known"]))

    def test_all_known_includes_chrome_and_firefox_and_safari(self, client):
        c, _ = client
        data = c.get("/wrappers").get_json()
        names = data["all_known"]
        assert any("chrome" in w for w in names)
        assert any("firefox" in w for w in names)
        assert any("safari" in w for w in names)


class TestFetch:
    def _mock_subprocess(self, stdout="", returncode=0):
        result = MagicMock()
        result.stdout = stdout
        result.stderr = ""
        result.returncode = returncode
        return result

    def test_missing_url_returns_400(self, client):
        c, _ = client
        r = c.post("/fetch", json={})
        assert r.status_code == 400
        assert "url is required" in r.get_json()["error"]

    def test_json_response_parsed(self, client):
        c, _ = client
        payload = {"url": "https://httpbin.org/get"}
        fake_body = json.dumps({"origin": "1.2.3.4"})
        mock_result = self._mock_subprocess(stdout=fake_body)
        with patch("subprocess.run", return_value=mock_result):
            r = c.post("/fetch", json=payload)
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        assert data["data"] == {"origin": "1.2.3.4"}

    def test_raw_text_fallback(self, client):
        c, _ = client
        with patch("subprocess.run", return_value=self._mock_subprocess(stdout="<html>ok</html>")):
            r = c.post("/fetch", json={"url": "https://example.com"})
        assert r.status_code == 200
        assert r.get_json()["data"] == "<html>ok</html>"

    def test_uses_specified_wrapper(self, client):
        c, _ = client
        with patch("subprocess.run", return_value=self._mock_subprocess(stdout="{}")) as mock_run:
            c.post("/fetch", json={"url": "https://example.com", "wrapper": "curl_chrome116"})
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "curl_chrome116"

    def test_uses_default_wrapper_when_not_specified(self, client):
        c, _ = client
        with patch("subprocess.run", return_value=self._mock_subprocess(stdout="{}")) as mock_run:
            c.post("/fetch", json={"url": "https://example.com"})
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "curl_chrome145"

    def test_unknown_wrapper_returns_400(self, client):
        c, _ = client
        r = c.post("/fetch", json={"url": "https://example.com", "wrapper": "curl_does_not_exist"})
        assert r.status_code == 400
        assert "not found" in r.get_json()["error"]

    def test_custom_headers_passed_to_curl(self, client):
        c, _ = client
        with patch("subprocess.run", return_value=self._mock_subprocess(stdout="{}")) as mock_run:
            c.post("/fetch", json={
                "url": "https://example.com",
                "headers": {"X-Custom": "value"}
            })
        cmd = mock_run.call_args[0][0]
        assert "-H" in cmd
        assert "X-Custom: value" in cmd

    def test_post_method_with_dict_data(self, client):
        c, _ = client
        with patch("subprocess.run", return_value=self._mock_subprocess(stdout="{}")) as mock_run:
            c.post("/fetch", json={
                "url": "https://example.com",
                "method": "POST",
                "data": {"key": "value"}
            })
        cmd = mock_run.call_args[0][0]
        assert "-X" in cmd
        assert "POST" in cmd
        assert "-d" in cmd
        data_idx = cmd.index("-d")
        assert json.loads(cmd[data_idx + 1]) == {"key": "value"}

    def test_curl_nonzero_returncode_returns_502(self, client):
        c, _ = client
        with patch("subprocess.run", return_value=self._mock_subprocess(stdout="", returncode=6)):
            r = c.post("/fetch", json={"url": "https://example.com"})
        assert r.status_code == 502
        assert r.get_json()["success"] is False

    def test_timeout_returns_504(self, client):
        c, _ = client
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=30)):
            r = c.post("/fetch", json={"url": "https://example.com"})
        assert r.status_code == 504


# ── Integration tests (require running container at localhost:5555) ────────────

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

BASE_URL = "http://localhost:5555"


@pytest.mark.integration
@pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
class TestIntegration:
    def test_health_endpoint(self):
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["default_wrapper"] is not None
        assert len(data["available_wrappers"]) > 0

    def test_wrappers_endpoint(self):
        r = requests.get(f"{BASE_URL}/wrappers", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert len(data["available"]) > 0
        assert len(data["all_known"]) > 0

    def test_fetch_httpbin(self):
        r = requests.post(f"{BASE_URL}/fetch", json={"url": "https://httpbin.org/get"}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert isinstance(data["data"], dict)
        assert "url" in data["data"]

    def test_fetch_missing_url(self):
        r = requests.post(f"{BASE_URL}/fetch", json={}, timeout=5)
        assert r.status_code == 400

    def test_fetch_invalid_wrapper(self):
        r = requests.post(f"{BASE_URL}/fetch", json={
            "url": "https://httpbin.org/get",
            "wrapper": "curl_does_not_exist"
        }, timeout=5)
        assert r.status_code == 400
