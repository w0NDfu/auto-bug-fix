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
validation, and an audit-ready domain model.

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
 | +--> #2 RepositoryWorkspace
 +----> #3 FailureEvidence
          \       /
           +--> #4 Fault localization
                    -> #5 Context retrieval
                    -> #6 PatchProposal
                    -> #7 Patch validation
                    -> #8 Sandbox
                    -> #9 Audit trace / RepairReport
                    -> #10 GitHub workflow
                    -> #11 Draft PR
                    -> #12 Benchmark + release
```

Dependencies guide sequencing but do not prohibit parallel work when an issue
can be implemented independently.

## Roadmap issues

The twelve substantive milestones are tracked in GitHub. Issue numbers and
links are recorded here after reconciliation with the remote repository.

The intended issue set is:

1. `chore: establish open-source engineering foundation`
2. `feat: support arbitrary local repositories with RepositoryWorkspace`
3. `feat: normalize failures into structured RepairRequest and FailureEvidence`
4. `feat: implement evidence-based Python fault localization`
5. `feat: build repository-aware context retrieval`
6. `refactor: introduce structured PatchProposal and unified diff generation`
7. `feat: validate generated patches before execution`
8. `security: add isolated Docker sandbox for candidate validation`
9. `feat: add auditable repair event trace and RepairReport`
10. `feat: integrate GitHub issue and CI failure workflows`
11. `feat: generate reviewed candidate fixes as draft pull requests`
12. `benchmark: establish reproducible repair evaluation and v0.1 release criteria`
