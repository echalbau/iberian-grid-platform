"""Client for REData, the public API of Red Eléctrica (no API key needed).

API reference: https://www.ree.es/en/datos/apidata
URL shape:     {base}/{lang}/datos/{category}/{widget}?start_date=...&end_date=...&time_trunc=...
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

import requests
from tenacity.wait import wait_base

from grid_platform.common.log import get_logger
from grid_platform.ingestion.http import RawResponse, SourceError, get_with_retries

BASE_URL = "https://apidatos.ree.es"
SOURCE = "ree"
DEMAND_DATASET = "demand"

logger = get_logger(__name__)


class REDataClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        base_url: str = BASE_URL,
        lang: str = "en",
        retry_wait: wait_base | None = None,
    ) -> None:
        self._session = session or requests.Session()
        self._base_url = base_url.rstrip("/")
        # English series titles ("Real", "Forecasted", ...). Series ids are the
        # same in every language and are what silver keys on.
        self._lang = lang
        self._retry_wait = retry_wait

    def fetch_widget(
        self, category: str, widget: str, day: date, *, time_trunc: str = "hour"
    ) -> RawResponse:
        """Fetch one local calendar day of a REData widget and validate its shape."""
        url = f"{self._base_url}/{self._lang}/datos/{category}/{widget}"
        params = {
            # REData interprets these as Spanish peninsular local time.
            "start_date": f"{day.isoformat()}T00:00",
            "end_date": f"{day.isoformat()}T23:59",
            "time_trunc": time_trunc,
        }
        response = get_with_retries(self._session, url, params, wait=self._retry_wait)
        raw = RawResponse(body=response.content, url=response.url, fetched_at=datetime.now(UTC))
        points = _count_points(raw.body)
        logger.info("Fetched %s/%s for %s: %d data points", category, widget, day, points)
        return raw

    def fetch_demand(self, day: date) -> RawResponse:
        """Real-time peninsular demand: real, forecasted and scheduled series
        at 5-minute resolution (the API ignores coarser ``time_trunc`` here)."""
        return self.fetch_widget("demanda", "demanda-tiempo-real", day)

    def fetch_generation(self, day: date) -> RawResponse:
        # TODO: widget `generacion/estructura-generacion` (daily resolution) -
        # decide whether the 5-minute generation mix needs a different source.
        raise NotImplementedError("REE generation ingestion is not implemented yet")

    def fetch_prices(self, day: date) -> RawResponse:
        # TODO: widget `mercados/precios-mercados-tiempo-real` (PVPC + spot).
        raise NotImplementedError("REE price ingestion is not implemented yet")


def _count_points(body: bytes) -> int:
    """Check the JSON:API envelope and return the number of data points.

    Raises ``SourceError`` when there is nothing worth storing, so a bad
    response never overwrites a good bronze partition.
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SourceError("REData response is not valid JSON") from exc

    included = payload.get("included") if isinstance(payload, dict) else None
    if not isinstance(included, list) or not included:
        raise SourceError("REData response has no 'included' series")

    try:
        points = sum(len(series["attributes"]["values"]) for series in included)
    except (KeyError, TypeError) as exc:
        raise SourceError("REData series is missing 'attributes.values'") from exc
    if points == 0:
        raise SourceError("REData response contains no data points")
    return points
