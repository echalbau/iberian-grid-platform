"""Runtime settings, read from environment variables only.

AWS credentials are deliberately not modelled here: boto3, Spark and DuckDB all
pick them up from the standard ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY``
variables (or an instance/role profile on AWS).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_BUCKET = "iberian-grid-lakehouse"
DEFAULT_REGION = "eu-south-2"


@dataclass(frozen=True)
class Settings:
    lakehouse_bucket: str = DEFAULT_BUCKET
    # Set for MinIO (e.g. http://localhost:9000); None means real AWS S3.
    s3_endpoint_url: str | None = None
    aws_region: str = DEFAULT_REGION
    entsoe_api_token: str | None = None
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env

        def optional(name: str) -> str | None:
            # Docker Compose passes unset variables through as empty strings.
            return env.get(name, "").strip() or None

        return cls(
            lakehouse_bucket=optional("LAKEHOUSE_BUCKET") or DEFAULT_BUCKET,
            s3_endpoint_url=optional("S3_ENDPOINT_URL"),
            aws_region=optional("AWS_REGION") or DEFAULT_REGION,
            entsoe_api_token=optional("ENTSOE_API_TOKEN"),
            log_level=(optional("LOG_LEVEL") or "INFO").upper(),
        )
