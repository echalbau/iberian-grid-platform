from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from grid_platform.common.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"
TEST_BUCKET = "test-lakehouse"


@pytest.fixture
def ree_demand_body() -> bytes:
    """Real REData response for 2025-04-28, trimmed to 3 points per series."""
    return (FIXTURES / "ree_demand_2025-04-28_sample.json").read_bytes()


@pytest.fixture
def settings() -> Settings:
    return Settings(lakehouse_bucket=TEST_BUCKET, aws_region="eu-south-2")


@pytest.fixture
def s3_client(monkeypatch):
    """In-memory S3 with the lakehouse bucket already created."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        client = boto3.client("s3", region_name="eu-south-2")
        client.create_bucket(
            Bucket=TEST_BUCKET,
            CreateBucketConfiguration={"LocationConstraint": "eu-south-2"},
        )
        yield client
