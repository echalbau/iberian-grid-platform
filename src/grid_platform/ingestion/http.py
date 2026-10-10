"""Shared HTTP plumbing for the source clients."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import requests
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential
from tenacity.wait import wait_base

DEFAULT_TIMEOUT_SECONDS = 30
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class SourceError(RuntimeError):
    """A source API returned something we refuse to store in bronze."""


@dataclass(frozen=True)
class RawResponse:
    """An API response exactly as received, plus where and when it came from."""

    body: bytes
    url: str
    fetched_at: datetime


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, requests.HTTPError):
        return exc.response is not None and exc.response.status_code in RETRYABLE_STATUS
    return isinstance(exc, requests.ConnectionError | requests.Timeout)


def get_with_retries(
    session: requests.Session,
    url: str,
    params: dict[str, str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    attempts: int = 4,
    wait: wait_base | None = None,
) -> requests.Response:
    """GET that retries transient failures (network errors, 429, 5xx) and
    raises ``requests.HTTPError`` for anything else that is not a 2xx."""
    retrying = Retrying(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(attempts),
        wait=wait if wait is not None else wait_exponential(multiplier=2, max=30),
        reraise=True,
    )
    for attempt in retrying:
        with attempt:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
    raise AssertionError("unreachable: Retrying always returns or raises")
