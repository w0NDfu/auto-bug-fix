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
- Offline normalization of bounded traceback, pytest, and raw failure evidence
  with `autobugfix inspect-failure`.

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

## Failure evidence inspection

Issue #3 adds a deterministic, offline normalization boundary for Python
tracebacks, pytest output, and raw failure logs:

```bash
autobugfix inspect-failure --log 'ValueError: invalid input' --json
```

The result contains serializable `RepairRequest`, `FailureEvidence`,
`StackFrame`, and `SourceLocation` data. Logs and optional issue text are
bounded and treated as hostile input: malformed UTF-8, oversized input, empty
input, and terminal control characters return structured validation errors.
Traceback frames are recognized only inside an explicit Python traceback
section; an indented line immediately following a frame is retained as its
source excerpt, while exception summaries, separators, blank lines, and other
log lines are not. Traceback exception summaries preserve custom exception
class names, including chained summaries in observed order. Pytest and raw-log
classification remains conservative and does not upgrade a stray `File ...`
line into traceback evidence.
The normalizer never executes log content, reads repositories, calls a
provider, or makes network requests. Issue text is kept separate from factual
failure observations; root-cause inference and repair remain future work.

## Planned architecture

The target flow is structured failure evidence -> repository context -> minimal
`PatchProposal` -> deterministic validation -> isolated sandbox -> `RepairReport`.
See [docs/architecture-v2.md](docs/architecture-v2.md) and
[docs/security-model.md](docs/security-model.md).

## Roadmap

See [ROADMAP.md](ROADMAP.md). RepositoryWorkspace inspection and offline Issue
#3 failure evidence normalization are implemented; Issues #4–#12 remain future
work.

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
