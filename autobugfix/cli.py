"""Small CLI wrapper for the currently supported MVP pipeline."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autobugfix",
        description="Auto-Bug-Fix: an evolving, auditable repository-repair framework.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")
    demo = subparsers.add_parser(
        "mvp-fix",
        help="run the historical fixed-demo MVP pipeline (not arbitrary repositories)",
    )
    demo.add_argument("--log", required=True, help="failure log supplied to the MVP pipeline")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "mvp-fix":
        from backend.core.orchestrator import run_pipeline

        print(json.dumps(run_pipeline(args.log), indent=2))
    else:
        build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

