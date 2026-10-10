"""Logging setup shared by CLI entrypoints and jobs."""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once. Airflow installs its own handlers, so this
    is a no-op there and task logs keep going to the Airflow task log."""
    logging.basicConfig(level=level, format=LOG_FORMAT)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
