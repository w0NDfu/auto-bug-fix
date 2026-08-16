# Security Policy

## Current status

The current MVP is not a security boundary. It writes model-provided source
and tests to a temporary directory and invokes host `pytest`. Do not use it
with untrusted prompts, repositories, or generated code.

## Reporting a vulnerability

Please do not disclose security-sensitive details in a public issue. Contact
the repository maintainers privately through the GitHub repository's available
security contact channels. Include reproduction steps and affected versions.

## Scope

The target design requires isolated, network-disabled candidate execution and
an auditable trace. Those protections are roadmap work and must not be inferred
from the current MVP.

