# Contributing to Auto-Bug-Fix

Auto-Bug-Fix is evolving from an educational MVP into a safe, auditable
repository-level repair framework. Please read `docs/mvp-baseline.md`,
`docs/architecture-v2.md`, `ROADMAP.md`, and `AGENTS.md` before making changes.

## Development

Create a virtual environment, install the package in editable mode, and run:

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
mypy autobugfix
autobugfix --help
```

Keep changes focused on one roadmap issue. Add behavioral tests, document
security implications, and do not include credentials or generated artifacts.

Ruff currently checks the foundation package and tests. The historical
`backend/` and demo `repo/` trees are excluded because bringing their existing
style and typing under the new gate would create an unrelated legacy cleanup;
that scope is explicit rather than being presented as full-repository lint
coverage.

## Pull requests

Explain the motivation, scope, validation, and known limitations. Generated
repairs remain proposals for human review; contributors must not add automatic
merge behavior.
