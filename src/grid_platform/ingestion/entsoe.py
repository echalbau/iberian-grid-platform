"""Client for the ENTSO-E Transparency Platform RESTful API (stub).

Needs a personal security token (``ENTSOE_API_TOKEN``). Responses are XML.
"""

from __future__ import annotations

from datetime import date

import requests

from grid_platform.ingestion.http import RawResponse

BASE_URL = "https://web-api.tp.entsoe.eu/api"
SOURCE = "entsoe"
PHYSICAL_FLOWS_DATASET = "physical_flows"

# Energy Identification Codes of the two bidding zones.
EIC_SPAIN = "10YES-REE------0"
EIC_PORTUGAL = "10YPT-REN------W"


class EntsoeClient:
    def __init__(self, api_token: str | None, session: requests.Session | None = None) -> None:
        if not api_token:
            raise ValueError("ENTSOE_API_TOKEN is required to call the ENTSO-E API")
        self._api_token = api_token
        self._session = session or requests.Session()

    def fetch_physical_flows(self, day: date, *, from_zone: str, to_zone: str) -> RawResponse:
        # TODO: GET BASE_URL with documentType=A11 (cross-border physical
        # flows), in_Domain/out_Domain set to the EIC codes above and
        # periodStart/periodEnd as UTC yyyyMMddHHmm covering the local day.
        # One request per direction; keep the XML untouched in bronze.
        raise NotImplementedError("ENTSO-E ingestion is not implemented yet")
