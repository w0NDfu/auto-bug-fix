# Roadmap

Auto-Bug-Fix began as a multi-agent repair prototype and is being incrementally
evolved into a safe, auditable, repository-level autonomous repair framework.
Release numbers below are goals, not claims.

## Stages

### Stage A — MVP baseline

The current historical prototype: a multi-agent demo with a fixed repository,
heuristic localization, simple retrieval, free-form patches, host-based test
execution, and limited tests.

### Stage B — Credible v0.1 OSS core

Proper package and CLI, CI, `RepositoryWorkspace`, structured failure evidence,
basic evidence-based Python localization, `PatchProposal`, deterministic
validation, and an audit-ready domain model. The current Issue #2 increment
delivers read-only local repository inspection; Issue #3 adds offline
structured failure evidence normalization; Issue #4 adds bounded,
evidence-based Python localization, while repair integration remains future
work. A deterministic Codex handoff adapter can compose these completed
inspection outputs for Codex without implementing context retrieval, patch
generation, or automatic execution.

### Stage C — Safe v0.2 repair engine

Docker sandbox, improved retrieval, repair iteration, `RepairReport`, security
model enforcement, and reproducible examples.

### Stage D — Stable v1.0 maintainer workflow

Stable CLI/API, optional GitHub integration, draft-PR workflow, extension
interfaces, benchmark suite, release process, and contributor documentation.

## Dependency graph

```text
#1 OSS foundation
 |\
 | +--> #2 RepositoryWorkspace --+
 +----> #3 FailureEvidence -----+--> #4 Fault localization
                                      -> #5 Context retrieval
                                      -> #6 PatchProposal
                                      -> #7 Patch validation --+--> #8 Sandbox
                                                               |      -> #9 Audit trace / RepairReport
                                                               |             -> #10 GitHub workflow
                                                               |                    -> #11 Draft PR
                                                               +--> #12 Benchmark + quality gates
```

Dependencies guide sequencing but do not prohibit parallel work when an issue
can be implemented independently. Issue numbers do not imply a strict
implementation order. In particular, benchmark and quality-gate work can
begin once the core workspace/evidence/patch/validation pipeline is measurable
and does not require the GitHub Draft PR workflow.

## Roadmap issues

The twelve substantive milestones are tracked in GitHub:

1. [#1 — chore: establish open-source engineering foundation](https://github.com/w0NDfu/auto-bug-fix/issues/1)
2. [#2 — feat: support arbitrary local repositories with RepositoryWorkspace](https://github.com/w0NDfu/auto-bug-fix/issues/2)
3. [#3 — feat: normalize failures into structured RepairRequest and FailureEvidence](https://github.com/w0NDfu/auto-bug-fix/issues/3)
4. [#4 — feat: implement evidence-based Python fault localization](https://github.com/w0NDfu/auto-bug-fix/issues/4)
5. [#5 — feat: build repository-aware context retrieval](https://github.com/w0NDfu/auto-bug-fix/issues/5)
6. [#6 — refactor: introduce structured PatchProposal and unified diff generation](https://github.com/w0NDfu/auto-bug-fix/issues/6)
7. [#7 — feat: validate generated patches before execution](https://github.com/w0NDfu/auto-bug-fix/issues/7)
8. [#8 — security: add isolated Docker sandbox for candidate validation](https://github.com/w0NDfu/auto-bug-fix/issues/8)
9. [#9 — feat: add auditable repair event trace and RepairReport](https://github.com/w0NDfu/auto-bug-fix/issues/9)
10. [#10 — feat: integrate GitHub issue and CI failure workflows](https://github.com/w0NDfu/auto-bug-fix/issues/10)
11. [#11 — feat: generate reviewed candidate fixes as draft pull requests](https://github.com/w0NDfu/auto-bug-fix/issues/11)
12. [#12 — benchmark: establish reproducible repair evaluation and release quality gates](https://github.com/w0NDfu/auto-bug-fix/issues/12)
