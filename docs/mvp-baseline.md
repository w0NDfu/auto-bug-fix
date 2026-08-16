# MVP baseline

This document records the state of Auto-Bug-Fix before the open-source
foundation work. The baseline is intentionally preserved so later releases can
show an honest evolution from prototype to repair framework.

## Existing MVP capabilities

- A FastAPI `POST /fix` endpoint accepts a log and runs a fixed orchestration loop.
- Planner, Locator, Retriever, Coder, Tester, Reflector, and Validator modules
  demonstrate the multi-agent concept.
- A mock provider gives a deterministic zero-division example without API access.
- An OpenAI-compatible provider can be selected through environment variables.
- The locator walks Python files in the bundled `repo/` demo and the retriever
  uses an in-memory TF-IDF index.
- Candidate source and test text is executed with a host `pytest` subprocess in
  a temporary directory.

## Existing limitations

- Localization is heuristic and assumes a repository directory literally named
  `repo/`; it does not support arbitrary workspaces or Git state.
- The system is Python-only and has no repository containment or ignore-rule
  model.
- Retrieval is keyword/TF-IDF based and has no structured symbol or evidence
  provenance.
- The coder returns free-form full-file text under `PATCH:` rather than a
  structured, hash-anchored diff.
- Generated tests execute on the host. The temporary directory is not a
  sandbox, and network, resource, and environment access are not restricted.
- There is no durable audit trail, repair report, reproducibility record, or
  safe candidate workspace separate from a user's original repository.
- Packaging, CLI, CI, contributor guidance, and release criteria were absent.
- GitHub issue, CI failure, and pull-request workflows are not implemented.

## Explicit non-capabilities

The MVP does not safely repair arbitrary repositories, guarantee patch
correctness, isolate generated code, disable network access, automatically
merge changes, create pull requests, or provide a research benchmark. The
mock provider is a deterministic demo, not evidence of general repair ability.

