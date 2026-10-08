import pytest

from pipeline import radar


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers))
        return self.response


SAMPLE = {
    "success": True,
    "result": {
        "meta": {"top": {"date": "2026-10-07"}, "lastUpdated": "2026-10-08T00:00:00Z"},
        "top": [
            {"rank": 1, "domain": "google.com", "categories": [{"id": 1, "name": "Search Engines"}]},
            {"rank": 2, "domain": "BBC.co.uk", "categories": []},
        ],
    },
}


def test_missing_token_skips_gracefully(monkeypatch):
    monkeypatch.delenv(radar.TOKEN_ENV, raising=False)
    with pytest.raises(radar.RadarUnavailable, match="CLOUDFLARE_API_TOKEN"):
        radar.fetch_top(location="GB")


def test_parses_ranking_and_sends_location():
    session = FakeSession(FakeResponse(200, SAMPLE))
    df, meta = radar.fetch_top(location="GB", token="t", session=session)
    assert df["domain"].tolist() == ["google.com", "bbc.co.uk"]
    assert df["rank"].tolist() == [1, 2]
    url, params, headers = session.calls[0]
    assert url == radar.API_URL
    assert params["location"] == "GB" and params["rankingType"] == "POPULAR"
    assert headers["Authorization"] == "Bearer t"
    assert radar.attribution(meta, "GB")["list_date"] == "2026-10-07"


def test_api_error_raises_unavailable():
    body = {"success": False, "errors": [{"code": 10000, "message": "Authentication error"}]}
    with pytest.raises(radar.RadarUnavailable, match="HTTP 403"):
        radar.fetch_top(token="bad", session=FakeSession(FakeResponse(403, body)))
