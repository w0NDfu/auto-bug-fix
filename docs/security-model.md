# Security model

## CURRENT MVP SECURITY MODEL

The MVP is a demonstration, not a security boundary. It reads the bundled
`repo/` directory, writes model-provided source and test text into a temporary
directory, and starts host `pytest`. It does not enforce repository containment,
patch hashes, binary rejection, resource limits, network isolation, an
environment allowlist, or an audit trail. API keys are read by the provider
process and are not intended for generated tests, but no sandbox exists to
enforce that boundary. Do not run it with untrusted generated code.

The foundation phase makes this risk visible in documentation and contributor
guidance. It does not pretend to deliver isolation ahead of the sandbox issue.

## IMPLEMENTED REPOSITORY INSPECTION CONTROLS

The Issue #2 RepositoryWorkspace layer now provides a narrower inspection
boundary: Git root resolution, bounded deterministic Python enumeration,
path-aware containment checks, symlink target checks, conservative sensitive
file exclusions, UTF-8 reads, file/file-count limits, and read-only Git-state
inspection. It does not use git status, git diff-files, or another worktree
content-comparison command. Git metadata commands use explicit working
directories, captured output, timeouts, no shell execution, and per-process
fsmonitor/untracked-cache/optional-lock protections. Exact worktree dirty state
is therefore reported as unknown rather than guessed.

These controls protect inspection operations only. They do not validate patches,
run repository tests, isolate processes, or make the existing MVP repair loop
safe. The source-file limit bounds eligible Python files, but total directory
traversal entries and scan time are not yet governed by a separate global
budget.

The Issue #3 failure normalizer is a separate offline boundary. It accepts
bounded UTF-8 text, rejects malformed/oversized/control-character input, and
parses traceback and test-output facts without executing the input or making
network/provider calls. Optional issue text remains separate from observed
failure evidence. It does not infer root causes or apply repairs.

The Issue #4 Python localizer adds another inspection-only boundary. Traceback
paths are mapped lexically to the bounded `RepositoryWorkspace` file index;
external or ambiguous paths are not read. Candidate source is read only via
`RepositoryWorkspace.read_text()` and parsed with `ast.parse`, never imported
or executed. Processing is bounded and deterministic. Localization evidence
does not establish a root cause and is not connected to patch generation or
repair orchestration.

## TARGET SECURITY MODEL

The target repair engine will:

1. resolve and contain all repository paths;
2. work from a disposable copy and never modify the original before validation;
3. validate structured, size-limited, text-only patches against base hashes;
4. reject traversal and binary changes by default;
5. run candidate tests in a disposable sandbox with network disabled, bounded
   CPU/memory/processes, timeouts, and an explicit environment allowlist;
6. keep API credentials outside sandbox environments unless a user explicitly
   permits otherwise;
7. capture stdout, stderr, commands, decisions, evidence, and failures in a
   human-readable and JSON repair report;
8. require human review for any proposed GitHub pull request and never merge
   automatically.

Docker isolation and the complete policy enforcement are roadmap work. Until
implemented and tested, the MVP must be treated as unsafe for untrusted code.

