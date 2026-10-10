import json
from datetime import date

import pytest
import requests
import responses
from tenacity import wait_none

from grid_platform.ingestion.http import SourceError
from grid_platform.ingestion.ree import BASE_URL, REDataClient

DEMAND_URL = f"{BASE_URL}/en/datos/demanda/demanda-tiempo-real"
DAY = date(2025, 4, 28)


@pytest.fixture
def client() -> REDataClient:
    return REDataClient(retry_wait=wait_none())


@responses.activate
def test_fetch_demand_requests_the_full_local_day(client, ree_demand_body):
    responses.get(DEMAND_URL, body=ree_demand_body)

    raw = client.fetch_demand(DAY)

    assert raw.body == ree_demand_body
    query = responses.calls[0].request.params
    assert query == {
        "start_date": "2025-04-28T00:00",
        "end_date": "2025-04-28T23:59",
        "time_trunc": "hour",
    }
    assert raw.fetched_at.tzinfo is not None


@responses.activate
def test_transient_errors_are_retried(client, ree_demand_body):
    responses.get(DEMAND_URL, status=502)
    responses.get(DEMAND_URL, body=requests.ConnectionError("boom"))
    responses.get(DEMAND_URL, body=ree_demand_body)

    assert client.fetch_demand(DAY).body == ree_demand_body
    assert len(responses.calls) == 3


@responses.activate
def test_gives_up_after_repeated_server_errors(client):
    responses.get(DEMAND_URL, status=502)

    with pytest.raises(requests.HTTPError):
        client.fetch_demand(DAY)
    assert len(responses.calls) == 4


@responses.activate
def test_client_errors_are_not_retried(client):
    responses.get(DEMAND_URL, status=400)

    with pytest.raises(requests.HTTPError):
        client.fetch_demand(DAY)
    assert len(responses.calls) == 1


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"<html>maintenance</html>", "not valid JSON"),
        (json.dumps({"errors": [{"status": "502"}]}).encode(), "no 'included' series"),
        (json.dumps({"included": [{"id": "2037"}]}).encode(), "missing 'attributes.values'"),
        (
            json.dumps({"included": [{"attributes": {"values": []}}]}).encode(),
            "no data points",
        ),
    ],
)
@responses.activate
def test_unusable_payloads_are_rejected(client, body, message):
    responses.get(DEMAND_URL, body=body)

    with pytest.raises(SourceError, match=message):
        client.fetch_demand(DAY)


@pytest.mark.parametrize("method", ["fetch_generation", "fetch_prices"])
def test_unimplemented_datasets_say_so(client, method):
    with pytest.raises(NotImplementedError):
        getattr(client, method)(DAY)
