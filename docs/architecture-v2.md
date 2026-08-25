# Auto-Bug-Fix architecture v2

The target architecture keeps the useful multi-agent responsibilities while
moving factual analysis and safety checks into typed, deterministic services.

Issues #2–#4 implement the first deterministic boundaries in this direction:
`RepositoryWorkspace` can inspect an existing local Git repository, failure
evidence is normalized offline, and Python traceback frames can be ranked as
bounded candidate locations without connecting localization to the LLM repair
loop. `CodexHandoff` composes those observations into a task package for Codex
without invoking Codex, selecting a model, or granting new permissions.

```text
Issue / failure / CI error / traceback
                 -> RepairRequest -> FailureEvidence
RepositoryWorkspace -> localization + context retrieval
                 -> CodexHandoff -> Codex inspection + human-reviewed change
                 -> ContextBuilder -> CodingAgent -> PatchProposal
                 -> PatchValidator -> IsolatedSandbox
                 -> ValidationResult -> RepairReport -> local CLI / draft PR
```

## Domain model direction

The core will progressively introduce serializable models for
`RepairRequest`, `FailureEvidence`, `StackFrame`, `SourceLocation`,
`RepositoryWorkspace`, `RepositoryContext`, `ContextEvidence`,
`PatchProposal`, `PatchFileChange`, `ValidationResult`, `RepairAttempt`,
`RepairEvent`, and `RepairReport`. Models must remain independent of any one
LLM vendor. Evidence and model inference must be represented separately, and
generated changes must carry provenance.

## Responsibilities

- Planner decomposes a repair goal.
- Locator ranks likely locations from traceback and repository evidence.
- Retriever builds bounded repository context.
- Coder proposes a minimal structured patch.
- Validator checks paths, hashes, diff shape, and policy limits.
- Tester runs approved candidates in an isolated runner.
- Reflector explains failed validation and prepares a next attempt.

These are responsibilities, not a requirement to add more agent classes. No
manager, supervisor, router, or judge abstraction is planned without a concrete
need.

The Issue #4 localizer is Python-only and evidence-based. Its ranked locations
are explainable candidates, not semantic root-cause verdicts. It does not
generate patches, execute repository code, or implement Issue #5 context
retrieval.

The Codex handoff is a boundary adapter, not a new repair orchestrator. It
serializes repository metadata, `RepairRequest`, localization output, and an
operating contract. Codex must still read `AGENTS.md`, inspect current state,
request permissions through its own environment, run validation, and leave
merge decisions to a human.

## Safety invariants

The original repository is never modified before validation. Candidate patches
are applied to an isolated workspace, generated changes are size-limited,
binary changes are rejected by default, and every attempt emits an audit event.
The production runner will disable network access and require explicit policy
for credentials. Automatic merging is outside the product boundary.

## Evolution

The implementation proceeds from the educational MVP to an OSS foundation,
then repository-level evidence and structured patches, deterministic
validation, isolated execution, auditability, GitHub maintainer workflows, and
finally reproducible evaluation. Current files do not yet implement the target
repair architecture; the workspace is currently inspection-only. See
`ROADMAP.md` for staged work.

