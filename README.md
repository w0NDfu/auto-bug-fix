# Auto-Bug-Fix

Auto-Bug-Fix is an evolving open-source project for safe, auditable,
repository-level bug repair. It began as an educational multi-agent MVP and is
being developed incrementally toward a framework that proposes and validates
minimal fixes while keeping humans in control of merges.

## Status

Early-stage foundation work. The current implementation is a fixed-demo MVP;
the target repository-level and sandboxed workflow is roadmap work.

## Current capabilities

- FastAPI `POST /fix` endpoint for the historical demo pipeline.
- Planner, locator, retriever, coder, tester, reflector, and validator modules.
- Deterministic mock provider and optional OpenAI-compatible provider.
- Basic Python AST and TF-IDF utilities retained from the MVP.
- Installable package and `autobugfix --help` CLI foundation.
- Read-only inspection of an existing local Git repository with
  `autobugfix inspect-repo`.

## How it works today

The MVP accepts a failure log, uses heuristic localization against the bundled
`repo/` demo, retrieves text with TF-IDF, asks a provider for a free-form patch
and tests, then repeats after a reflection hint. This is not arbitrary-repository
repair and generated tests run on the host.

Repository inspection is a separate foundation capability. It resolves a local
Git root, records basic Git state, enumerates bounded UTF-8 Python files, and
supports contained reads. It does not send a repository to an LLM, execute
repository code, generate a patch, or repair the repository.

## Installation

```bash
python -m pip install -e .
```

## Quick start

Use the explicit MVP command with the offline provider:

```bash
python -m pip install -e ".[dev]"
set LLM_PROVIDER=mock
autobugfix mvp-fix --log "ZeroDivisionError: division by zero"
```

The FastAPI demo remains available with `uvicorn backend.main:app --reload`.
The `openai` provider requires credentials and may make external requests.

## Mock / offline mode

The default mock provider makes no LLM network request and is the required mode
for tests. It only covers the bundled zero-division demonstration.

## Safety

The current MVP is not a sandbox and must not be treated as safe for untrusted
code. It can execute generated tests through host `pytest`. Do not provide
secrets to generated code. Network-disabled Docker execution, structured patch
validation, and audit reports are planned, not implemented.

`inspect-repo` improves the safety of local inspection through path containment,
symlink checks, sensitive-file exclusions, and resource bounds, but it does not
make the overall MVP repair loop safe. Its source-file limit does not yet impose
a separate global directory-entry or traversal-time budget.

## Inspect a local repository

```bash
autobugfix inspect-repo /path/to/repository
autobugfix inspect-repo /path/to/repository --json
```

This command is inspection-only. It accepts a repository root, nested path, or
file inside an existing Git repository and reports its root, HEAD, branch
state, eligible Python-file count, ignored entries, and warnings. Exact
worktree dirty state is intentionally reported as unknown because inspection
does not execute Git worktree-content filters. Repository-level autonomous
repair is not implemented.

## Planned architecture

The target flow is structured failure evidence -> repository context -> minimal
`PatchProposal` -> deterministic validation -> isolated sandbox -> `RepairReport`.
See [docs/architecture-v2.md](docs/architecture-v2.md) and
[docs/security-model.md](docs/security-model.md).

## Roadmap

See [ROADMAP.md](ROADMAP.md). RepositoryWorkspace inspection is the current
Issue #2 milestone; Issues #3–#12 remain future work.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check .
mypy autobugfix
autobugfix --help
autobugfix --version
```

The Ruff foundation gate intentionally excludes the historical `backend/` and
demo `repo/` trees; this is documented in [CONTRIBUTING.md](CONTRIBUTING.md)
and is not a claim of full-repository lint coverage.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and
[SECURITY.md](SECURITY.md) before changing the project.

## License

MIT. See [LICENSE](LICENSE).
