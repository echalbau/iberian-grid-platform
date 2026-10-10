from datetime import UTC, date, datetime

import pytest
import responses
from tenacity import wait_none

from grid_platform.cli import build_parser
from grid_platform.ingestion.bronze import ingest_ree_demand, write_bronze
from grid_platform.ingestion.http import RawResponse, SourceError
from grid_platform.ingestion.ree import BASE_URL, REDataClient
from tests.conftest import TEST_BUCKET

DEMAND_URL = f"{BASE_URL}/en/datos/demanda/demanda-tiempo-real"
DAY = date(2025, 4, 28)
KEY = "bronze/ree/demand/date=2025-04-28/data.json"


def _raw(body: bytes) -> RawResponse:
    return RawResponse(body=body, url="https://example.test/x", fetched_at=datetime.now(UTC))


def _keys(s3_client) -> list[str]:
    listing = s3_client.list_objects_v2(Bucket=TEST_BUCKET)
    return [obj["Key"] for obj in listing.get("Contents", [])]


def test_write_bronze_stores_body_untouched_with_lineage_metadata(s3_client):
    key = write_bronze(s3_client, TEST_BUCKET, "ree", "demand", DAY, _raw(b'{"a": 1}'))

    stored = s3_client.get_object(Bucket=TEST_BUCKET, Key=key)
    assert key == KEY
    assert stored["Body"].read() == b'{"a": 1}'
    assert stored["Metadata"]["source-url"] == "https://example.test/x"
    assert "fetched-at" in stored["Metadata"]


def test_rerunning_a_day_overwrites_instead_of_duplicating(s3_client):
    write_bronze(s3_client, TEST_BUCKET, "ree", "demand", DAY, _raw(b"first"))
    write_bronze(s3_client, TEST_BUCKET, "ree", "demand", DAY, _raw(b"second"))

    assert _keys(s3_client) == [KEY]
    assert s3_client.get_object(Bucket=TEST_BUCKET, Key=KEY)["Body"].read() == b"second"


def test_each_day_gets_its_own_partition(s3_client):
    write_bronze(s3_client, TEST_BUCKET, "ree", "demand", DAY, _raw(b"a"))
    write_bronze(s3_client, TEST_BUCKET, "ree", "demand", date(2025, 4, 29), _raw(b"b"))

    assert _keys(s3_client) == [KEY, "bronze/ree/demand/date=2025-04-29/data.json"]


@responses.activate
def test_ingest_ree_demand_end_to_end(s3_client, settings, ree_demand_body):
    responses.get(DEMAND_URL, body=ree_demand_body)

    uri = ingest_ree_demand(DAY, settings=settings, s3_client=s3_client)

    assert uri == f"s3://{TEST_BUCKET}/{KEY}"
    assert s3_client.get_object(Bucket=TEST_BUCKET, Key=KEY)["Body"].read() == ree_demand_body


@responses.activate
def test_bad_response_does_not_overwrite_existing_partition(s3_client, settings):
    write_bronze(s3_client, TEST_BUCKET, "ree", "demand", DAY, _raw(b"good"))
    responses.get(DEMAND_URL, json={"errors": [{"status": "502"}]})

    with pytest.raises(SourceError):
        ingest_ree_demand(
            DAY,
            settings=settings,
            s3_client=s3_client,
            ree_client=REDataClient(retry_wait=wait_none()),
        )
    assert s3_client.get_object(Bucket=TEST_BUCKET, Key=KEY)["Body"].read() == b"good"


def test_cli_parses_ingest_command():
    args = build_parser().parse_args(["ingest", "ree-demand", "--date", "2025-04-28"])

    assert (args.command, args.dataset, args.date) == ("ingest", "ree-demand", DAY)
