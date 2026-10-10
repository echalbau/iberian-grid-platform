"""Bronze writer: one raw object per (source, dataset, day)."""

from __future__ import annotations

from datetime import date
from typing import Any

from grid_platform.common import paths
from grid_platform.common.config import Settings
from grid_platform.common.log import get_logger
from grid_platform.common.s3 import make_s3_client, put_bytes
from grid_platform.ingestion.http import RawResponse
from grid_platform.ingestion.ree import DEMAND_DATASET, SOURCE, REDataClient

logger = get_logger(__name__)


def write_bronze(
    s3_client: Any,
    bucket: str,
    source: str,
    dataset: str,
    day: date,
    raw: RawResponse,
    *,
    content_type: str = "application/json",
) -> str:
    """Store a raw response under its deterministic key and return the key.

    Idempotent: the key depends only on (source, dataset, day), so re-running a
    day replaces the object instead of adding another one.
    """
    key = paths.bronze_object_key(source, dataset, day)
    put_bytes(
        s3_client,
        bucket,
        key,
        raw.body,
        content_type=content_type,
        # Lineage lives in object metadata so the body stays byte-identical
        # to what the API returned.
        metadata={"source-url": raw.url, "fetched-at": raw.fetched_at.isoformat()},
    )
    logger.info("Wrote %d bytes to %s", len(raw.body), paths.s3_uri(bucket, key))
    return key


def ingest_ree_demand(
    day: date,
    *,
    settings: Settings | None = None,
    ree_client: REDataClient | None = None,
    s3_client: Any | None = None,
) -> str:
    """Fetch one day of REE demand and land it in bronze. Returns the S3 URI."""
    settings = settings or Settings.from_env()
    ree_client = ree_client or REDataClient()
    s3_client = s3_client or make_s3_client(settings)

    raw = ree_client.fetch_demand(day)
    key = write_bronze(s3_client, settings.lakehouse_bucket, SOURCE, DEMAND_DATASET, day, raw)
    return paths.s3_uri(settings.lakehouse_bucket, key)
