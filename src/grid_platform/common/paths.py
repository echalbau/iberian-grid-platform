"""Lakehouse layout. This module is the code side of ``docs/data_contract.md``.

    s3://<bucket>/bronze/<source>/<dataset>/date=YYYY-MM-DD/data.json
    s3://<bucket>/silver/<table>/date=YYYY-MM-DD/part-*.parquet
    s3://<bucket>/gold/<model>/...

Keys are deterministic for a given (dataset, day), which is what makes re-runs
overwrite a partition instead of appending to it.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

PARTITION_COLUMN = "date"
BRONZE_FILENAME = "data.json"


class Layer(StrEnum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


def date_partition(day: date) -> str:
    return f"{PARTITION_COLUMN}={day.isoformat()}"


def bronze_dataset_prefix(source: str, dataset: str) -> str:
    return f"{Layer.BRONZE}/{source}/{dataset}/"


def bronze_partition_prefix(source: str, dataset: str, day: date) -> str:
    return f"{bronze_dataset_prefix(source, dataset)}{date_partition(day)}/"


def bronze_object_key(source: str, dataset: str, day: date) -> str:
    """Key of the single raw object holding one day of one dataset."""
    return f"{bronze_partition_prefix(source, dataset, day)}{BRONZE_FILENAME}"


def silver_table_prefix(table: str) -> str:
    return f"{Layer.SILVER}/{table}/"


def gold_table_prefix(model: str) -> str:
    return f"{Layer.GOLD}/{model}/"


def s3_uri(bucket: str, key: str, scheme: str = "s3") -> str:
    """Build a URI for a key. Use ``scheme="s3a"`` for Spark/Hadoop."""
    return f"{scheme}://{bucket}/{key}"
