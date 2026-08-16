"""Small CLI wrapper for the currently supported MVP pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import __version__
from .workspace import RepositoryWorkspace, WorkspaceError, format_summary


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
    inspect = subparsers.add_parser(
        "inspect-repo",
        help="inspect an existing local Git repository without executing or repairing it",
    )
    inspect.add_argument("path", help="repository root, nested path, or file inside a repository")
    inspect.add_argument("--json", action="store_true", help="emit deterministic JSON output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "mvp-fix":
        from backend.core.orchestrator import run_pipeline

        print(json.dumps(run_pipeline(args.log), indent=2))
    elif args.command == "inspect-repo":
        try:
            summary = RepositoryWorkspace.open(args.path).summary()
        except WorkspaceError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
        else:
            print(format_summary(summary))
    else:
        build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

