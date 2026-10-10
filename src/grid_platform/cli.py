"""Command line entrypoint: ``grid-platform ingest ree-demand --date 2025-04-28``."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from grid_platform.common.config import Settings
from grid_platform.common.dates import parse_day
from grid_platform.common.log import configure_logging
from grid_platform.ingestion.bronze import ingest_ree_demand


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grid-platform")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="Land one day of a dataset in bronze")
    datasets = ingest.add_subparsers(dest="dataset", required=True)
    ree_demand = datasets.add_parser("ree-demand", help="REE real-time demand")
    ree_demand.add_argument("--date", required=True, type=parse_day, help="YYYY-MM-DD")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    if args.command == "ingest" and args.dataset == "ree-demand":
        print(ingest_ree_demand(args.date, settings=settings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
