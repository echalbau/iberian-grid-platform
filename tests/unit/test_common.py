from datetime import UTC, date, datetime

import pytest

from grid_platform.common import paths
from grid_platform.common.config import DEFAULT_BUCKET, Settings
from grid_platform.common.dates import parse_day, resolve_target_day


class TestSettings:
    def test_defaults_when_environment_is_empty(self):
        settings = Settings.from_env({})

        assert settings.lakehouse_bucket == DEFAULT_BUCKET
        assert settings.s3_endpoint_url is None
        assert settings.entsoe_api_token is None
        assert settings.log_level == "INFO"

    def test_reads_values_from_environment(self):
        settings = Settings.from_env(
            {
                "LAKEHOUSE_BUCKET": "my-bucket",
                "S3_ENDPOINT_URL": "http://localhost:9000",
                "LOG_LEVEL": "debug",
            }
        )

        assert settings.lakehouse_bucket == "my-bucket"
        assert settings.s3_endpoint_url == "http://localhost:9000"
        assert settings.log_level == "DEBUG"

    def test_empty_strings_count_as_unset(self):
        settings = Settings.from_env({"S3_ENDPOINT_URL": "", "ENTSOE_API_TOKEN": "  "})

        assert settings.s3_endpoint_url is None
        assert settings.entsoe_api_token is None


class TestPaths:
    def test_bronze_object_key_is_deterministic_and_date_partitioned(self):
        key = paths.bronze_object_key("ree", "demand", date(2025, 4, 28))

        assert key == "bronze/ree/demand/date=2025-04-28/data.json"
        assert key == paths.bronze_object_key("ree", "demand", date(2025, 4, 28))

    def test_table_prefixes(self):
        assert paths.silver_table_prefix("ree_demand") == "silver/ree_demand/"
        assert paths.gold_table_prefix("fct_demand_hourly") == "gold/fct_demand_hourly/"

    def test_s3_uri_scheme(self):
        assert paths.s3_uri("b", "silver/t/") == "s3://b/silver/t/"
        assert paths.s3_uri("b", "silver/t/", scheme="s3a") == "s3a://b/silver/t/"


class TestDates:
    def test_explicit_day_wins(self):
        reference = datetime(2026, 1, 1, tzinfo=UTC)

        assert resolve_target_day("2025-04-28", reference) == date(2025, 4, 28)

    def test_defaults_to_previous_local_day(self):
        # 23:30 UTC on 28 April is already 01:30 on 29 April in Madrid (CEST).
        reference = datetime(2025, 4, 28, 23, 30, tzinfo=UTC)

        assert resolve_target_day(None, reference) == date(2025, 4, 28)

    def test_naive_reference_is_rejected(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            resolve_target_day(None, datetime(2025, 4, 28))

    @pytest.mark.parametrize("value", ["28-04-2025", "2025-4-31", "today", ""])
    def test_parse_day_rejects_bad_input(self, value):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            parse_day(value)
