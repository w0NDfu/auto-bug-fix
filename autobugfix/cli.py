"""Small CLI wrapper for the currently supported MVP pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import __version__
from .evidence import EvidenceValidationError
from .failure_normalizer import normalize_failure
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
    failure = subparsers.add_parser(
        "inspect-failure",
        aliases=["normalize-failure"],
        help="normalize hostile failure text without executing it",
    )
    failure.add_argument("--log", required=True, help="traceback, pytest output, or raw failure log")
    failure.add_argument("--issue-text", help="optional maintainer issue text kept separate from observations")
    failure.add_argument("--source", default="auto", help="evidence source label, or auto (default)")
    failure.add_argument("--json", action="store_true", help="emit deterministic JSON output")
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
    elif args.command in {"inspect-failure", "normalize-failure"}:
        try:
            request = normalize_failure(
                args.log,
                issue_text=args.issue_text,
                source=args.source,
            )
        except EvidenceValidationError as exc:
            print(json.dumps(exc.to_dict(), indent=2, sort_keys=True), file=sys.stderr)
            return 2
        if args.json:
            print(request.to_json(), end="")
        else:
            print(json.dumps(request.to_dict(), indent=2, sort_keys=True))
    else:
        build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

