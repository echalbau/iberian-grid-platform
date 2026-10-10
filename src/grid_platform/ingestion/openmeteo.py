"""Client for the Open-Meteo Historical Weather API (stub). No API key needed."""

from __future__ import annotations

from datetime import date

import requests

from grid_platform.ingestion.http import RawResponse

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCE = "openmeteo"
WEATHER_DATASET = "weather_hourly"


class OpenMeteoClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()

    def fetch_hourly_weather(self, day: date) -> RawResponse:
        # TODO: pick the list of locations (demand centres plus wind/solar
        # production areas) and the hourly variables (temperature_2m,
        # wind_speed_100m, shortwave_radiation), then call ARCHIVE_URL with
        # start_date=end_date=day and timezone=Europe/Madrid.
        raise NotImplementedError("Open-Meteo ingestion is not implemented yet")
