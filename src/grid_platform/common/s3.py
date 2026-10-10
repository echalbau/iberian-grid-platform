"""Thin boto3 helpers. The same code talks to MinIO locally and S3 on AWS."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config

from grid_platform.common.config import Settings


def make_s3_client(settings: Settings) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.aws_region,
        # MinIO is addressed as http://host:9000/<bucket>, not <bucket>.host.
        config=Config(s3={"addressing_style": "path"}) if settings.s3_endpoint_url else None,
    )


def put_bytes(
    client: Any,
    bucket: str,
    key: str,
    body: bytes,
    *,
    content_type: str = "application/octet-stream",
    metadata: dict[str, str] | None = None,
) -> None:
    """Write (or overwrite) one object. PutObject replaces the whole object
    atomically, so readers never see a partially written file."""
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
        Metadata=metadata or {},
    )
