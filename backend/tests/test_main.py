import httpx
import pytest

from app.main import app, normalize_url, is_valid_url

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_read_root(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "API Observatory backend is running"
    }


def test_normalize_url_adds_https_scheme():
    assert normalize_url("example.com") == "https://example.com"
    assert normalize_url("http://example.com") == "http://example.com"
    assert normalize_url("https://example.com") == "https://example.com"


def test_normalize_url_strips_spaces():
    assert normalize_url("  example.com  ") == "https://example.com"


def test_is_valid_url():
    assert is_valid_url("https://example.com") is True
    assert is_valid_url("http://localhost:8000") is True
    assert is_valid_url("not-a-url") is False
    assert is_valid_url("https://") is False
    assert is_valid_url("") is False


async def test_check_url_invalid_url_returns_invalid_status(client):
    response = await client.post("/check", json={"url": "https://"})

    assert response.status_code == 200

    body = response.json()

    assert body["url"] == "https://"
    assert body["status"] == "Invalid"
    assert body["status_code"] is None
    assert body["response_time_ms"] is None
    assert body["checked_at"] is not None
    assert body["message"] == "Please enter a valid URL."


async def test_check_url_empty_string_is_invalid(client):
    response = await client.post("/check", json={"url": ""})

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "Invalid"
    assert body["status_code"] is None
    assert body["response_time_ms"] is None
    assert body["checked_at"] is not None
    assert body["message"] == "Please enter a valid URL."


async def test_check_url_whitespace_only_is_invalid(client):
    response = await client.post("/check", json={"url": "   "})

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "Invalid"
    assert body["status_code"] is None
    assert body["response_time_ms"] is None
    assert body["checked_at"] is not None
    assert body["message"] == "Please enter a valid URL."


async def test_check_url_missing_url_returns_422(client):
    response = await client.post("/check", json={})

    assert response.status_code == 422


class DummyResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code


class DummyAsyncClient:
    def __init__(self, timeout=None, follow_redirects=False):
        self.timeout = timeout
        self.follow_redirects = follow_redirects

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        return DummyResponse(status_code=200)


async def test_check_url_with_up_response(monkeypatch, client):
    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    response = await client.post("/check", json={"url": "example.com"})

    assert response.status_code == 200

    body = response.json()

    assert body["url"] == "https://example.com"
    assert body["status"] == "Up"
    assert body["status_code"] == 200
    assert body["response_time_ms"] is not None
    assert body["checked_at"] is not None
    assert body["message"] == "Healthy response"


async def test_check_url_preserves_http_scheme(monkeypatch, client):
    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    response = await client.post("/check", json={"url": "http://example.com"})

    assert response.status_code == 200

    body = response.json()

    assert body["url"] == "http://example.com"
    assert body["status"] == "Up"
    assert body["status_code"] == 200


class DummyRedirectClient(DummyAsyncClient):
    def __init__(self, timeout=None, follow_redirects=False):
        super().__init__(timeout=timeout, follow_redirects=follow_redirects)
        assert follow_redirects is True


async def test_check_url_uses_follow_redirects(monkeypatch, client):
    monkeypatch.setattr(httpx, "AsyncClient", DummyRedirectClient)

    response = await client.post("/check", json={"url": "example.com"})

    assert response.status_code == 200
    assert response.json()["status"] == "Up"


class DummyStatusCodeClient(DummyAsyncClient):
    status_code_to_return = 200

    async def get(self, url):
        return DummyResponse(status_code=self.status_code_to_return)


@pytest.mark.parametrize(
    "status_code, expected_status, expected_message",
    [
        (199, "Up", "Healthy response"),
        (200, "Up", "Healthy response"),
        (300, "Up", "Healthy response"),
        (399, "Up", "Healthy response"),
        (400, "Warning", "Endpoint responded with an error status."),
        (599, "Warning", "Endpoint responded with an error status."),
    ],
)
async def test_check_url_status_code_boundaries(
    monkeypatch,
    client,
    status_code,
    expected_status,
    expected_message,
):
    class CustomStatusCodeClient(DummyStatusCodeClient):
        status_code_to_return = status_code

    monkeypatch.setattr(httpx, "AsyncClient", CustomStatusCodeClient)

    response = await client.post("/check", json={"url": "example.com"})

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == expected_status
    assert body["status_code"] == status_code
    assert body["response_time_ms"] is not None
    assert body["checked_at"] is not None
    assert body["message"] == expected_message


class DummyWarningClient(DummyAsyncClient):
    async def get(self, url):
        return DummyResponse(status_code=404)


async def test_check_url_with_warning_response(monkeypatch, client):
    monkeypatch.setattr(httpx, "AsyncClient", DummyWarningClient)

    response = await client.post("/check", json={"url": "example.com"})

    assert response.status_code == 200

    body = response.json()

    assert body["url"] == "https://example.com"
    assert body["status"] == "Warning"
    assert body["status_code"] == 404
    assert body["response_time_ms"] is not None
    assert body["checked_at"] is not None
    assert body["message"] == "Endpoint responded with an error status."


class DummyServerErrorClient(DummyAsyncClient):
    async def get(self, url):
        return DummyResponse(status_code=500)


async def test_check_url_with_server_error_response(monkeypatch, client):
    monkeypatch.setattr(httpx, "AsyncClient", DummyServerErrorClient)

    response = await client.post("/check", json={"url": "example.com"})

    assert response.status_code == 200

    body = response.json()

    assert body["url"] == "https://example.com"
    assert body["status"] == "Warning"
    assert body["status_code"] == 500
    assert body["response_time_ms"] is not None
    assert body["checked_at"] is not None
    assert body["message"] == "Endpoint responded with an error status."


class DummyTimeoutClient(DummyAsyncClient):
    async def get(self, url):
        raise httpx.TimeoutException("Request timed out")


async def test_check_url_timeout(monkeypatch, client):
    monkeypatch.setattr(httpx, "AsyncClient", DummyTimeoutClient)

    response = await client.post("/check", json={"url": "example.com"})

    assert response.status_code == 200

    body = response.json()

    assert body["url"] == "https://example.com"
    assert body["status"] == "Down"
    assert body["status_code"] is None
    assert body["response_time_ms"] is None
    assert body["checked_at"] is not None
    assert body["message"] == "Request timed out."


class DummyRequestErrorClient(DummyAsyncClient):
    async def get(self, url):
        raise httpx.RequestError("Could not connect")


async def test_check_url_request_error(monkeypatch, client):
    monkeypatch.setattr(httpx, "AsyncClient", DummyRequestErrorClient)

    response = await client.post("/check", json={"url": "example.com"})

    assert response.status_code == 200

    body = response.json()

    assert body["url"] == "https://example.com"
    assert body["status"] == "Down"
    assert body["status_code"] is None
    assert body["response_time_ms"] is None
    assert body["checked_at"] is not None
    assert body["message"] == "Could not connect to the URL."