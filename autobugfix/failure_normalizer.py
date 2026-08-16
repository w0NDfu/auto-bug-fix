"""Offline parsing of Python traceback, pytest, and raw failure logs."""

from __future__ import annotations

import re

from .evidence import (
    EvidenceLimits,
    EvidenceValidationError,
    FailureEvidence,
    RepairRequest,
    SourceLocation,
    StackFrame,
)

_TRACEBACK_HEADER = "Traceback (most recent call last):"
_FRAME_RE = re.compile(r'^\s*File ["\'](?P<file>.+?)["\'], line (?P<line>\d+)(?:, in (?P<function>.*))?\s*$')
_ERROR_RE = re.compile(
    r"^\s*(?:E\s+)?(?P<type>[A-Za-z_][\w.]*(?:Error|Exception|Exit|Warning))(?::\s*(?P<message>.*))?\s*$"
)
_PYTEST_FAILED_RE = re.compile(r"^\s*FAILED\s+(?P<test>\S+?)(?:\s+-\s+(?P<message>.*))?\s*$")
_ALLOWED_CONTROL_CHARS = {"\n", "\r", "\t"}


def normalize_failure(
    raw_log: str | bytes,
    *,
    issue_text: str | bytes | None = None,
    source: str = "auto",
    limits: EvidenceLimits | None = None,
) -> RepairRequest:
    """Normalize hostile failure text without execution, I/O, or network calls."""

    active_limits = limits or EvidenceLimits()
    normalized_log = _validate_text(raw_log, "raw_log", active_limits.max_input_bytes, active_limits)
    normalized_source = _validate_text(source, "source", 128, active_limits)
    normalized_issue = None
    if issue_text is not None:
        normalized_issue = _validate_text(
            issue_text,
            "issue_text",
            active_limits.max_issue_text_bytes,
            active_limits,
            allow_empty=True,
        )
        if not normalized_issue.strip():
            normalized_issue = None

    lines = normalized_log.split("\n")
    if len(lines) > active_limits.max_lines:
        raise EvidenceValidationError(
            "too_many_lines",
            f"input contains {len(lines)} lines; maximum is {active_limits.max_lines}",
            details={"actual": len(lines), "maximum": active_limits.max_lines},
        )
    frames = _parse_frames(lines, active_limits)
    messages = _parse_messages(lines)
    detected_source = _detect_source(lines) if normalized_source == "auto" else normalized_source
    parser = "python-traceback" if frames else ("pytest" if detected_source == "pytest" else "raw")
    confidence = 1.0 if frames else (0.8 if detected_source == "pytest" else 0.2)
    excerpts = _excerpts(lines, active_limits.max_excerpt_chars)
    evidence = FailureEvidence(
        source=detected_source,
        raw_log=normalized_log,
        frames=tuple(frames),
        message=messages[-1] if messages else None,
        excerpts=tuple(excerpts),
        parser=parser,
        parser_confidence=confidence,
    )
    return RepairRequest(evidence=evidence, issue_text=normalized_issue)


class FailureNormalizer:
    """Small dependency-free facade for callers that prefer an object API."""

    def __init__(self, limits: EvidenceLimits | None = None) -> None:
        self.limits = limits or EvidenceLimits()

    def normalize(
        self,
        raw_log: str | bytes,
        *,
        issue_text: str | bytes | None = None,
        source: str = "auto",
    ) -> RepairRequest:
        return normalize_failure(
            raw_log,
            issue_text=issue_text,
            source=source,
            limits=self.limits,
        )


def _validate_text(
    value: str | bytes,
    field_name: str,
    max_bytes: int,
    limits: EvidenceLimits,
    *,
    allow_empty: bool = False,
) -> str:
    if isinstance(value, bytes):
        if len(value) > max_bytes:
            raise EvidenceValidationError(
                "input_too_large",
                f"{field_name} exceeds the {max_bytes}-byte limit",
                field=field_name,
                details={"actual_bytes": len(value), "maximum_bytes": max_bytes},
            )
        try:
            text = value.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise EvidenceValidationError(
                "invalid_utf8",
                f"{field_name} is not valid UTF-8",
                field=field_name,
                details={"byte_offset": exc.start},
            ) from exc
    elif isinstance(value, str):
        try:
            encoded = value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise EvidenceValidationError(
                "invalid_unicode",
                f"{field_name} contains an invalid Unicode surrogate",
                field=field_name,
                details={"character_offset": exc.start},
            ) from exc
        if len(encoded) > max_bytes:
            raise EvidenceValidationError(
                "input_too_large",
                f"{field_name} exceeds the {max_bytes}-byte limit",
                field=field_name,
                details={"actual_bytes": len(encoded), "maximum_bytes": max_bytes},
            )
        text = value
    else:
        raise EvidenceValidationError(
            "invalid_type",
            f"{field_name} must be text or UTF-8 bytes",
            field=field_name,
        )
    if not allow_empty and not text.strip():
        raise EvidenceValidationError("empty_input", f"{field_name} must not be empty", field=field_name)
    for offset, character in enumerate(text):
        codepoint = ord(character)
        if (
            (codepoint < 0x20 and character not in _ALLOWED_CONTROL_CHARS)
            or codepoint == 0x7F
            or 0x80 <= codepoint <= 0x9F
        ):
            raise EvidenceValidationError(
                "control_character",
                f"{field_name} contains a disallowed control character",
                field=field_name,
                details={"character_offset": offset, "codepoint": f"U+{ord(character):04X}"},
            )
    if len(text.splitlines()) > limits.max_lines:
        raise EvidenceValidationError(
            "too_many_lines",
            f"{field_name} exceeds the {limits.max_lines}-line limit",
            field=field_name,
            details={"maximum": limits.max_lines},
        )
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _parse_frames(lines: list[str], limits: EvidenceLimits) -> list[StackFrame]:
    frames: list[StackFrame] = []
    for index, line in enumerate(lines):
        match = _FRAME_RE.match(line)
        if match is None:
            continue
        excerpt = _next_code_line(lines, index, limits.max_excerpt_chars)
        frames.append(
            StackFrame(
                location=SourceLocation(file=match.group("file"), line=int(match.group("line"))),
                function=match.group("function") or None,
                excerpt=excerpt,
            )
        )
    return frames


def _next_code_line(lines: list[str], index: int, maximum: int) -> str | None:
    if index + 1 >= len(lines):
        return None
    candidate = lines[index + 1].strip()
    if not candidate or candidate.startswith("File "):
        return None
    return candidate[:maximum]


def _parse_messages(lines: list[str]) -> list[str]:
    messages: list[str] = []
    for line in lines:
        match = _ERROR_RE.match(line)
        if match:
            error_type = match.group("type")
            message = match.group("message") or ""
            messages.append(f"{error_type}: {message}".rstrip())
            continue
        failed = _PYTEST_FAILED_RE.match(line)
        if failed and failed.group("message"):
            messages.append(f"pytest failure: {failed.group('message')}")
    return messages


def _detect_source(lines: list[str]) -> str:
    joined = "\n".join(lines)
    if _TRACEBACK_HEADER in joined:
        return "traceback"
    if any(_PYTEST_FAILED_RE.match(line) for line in lines) or any(line.lstrip().startswith("E   ") for line in lines):
        return "pytest"
    return "raw_log"


def _excerpts(lines: list[str], maximum: int) -> list[str]:
    return [line.strip()[:maximum] for line in lines if line.strip()][:3]


__all__ = [
    "FailureNormalizer",
    "normalize_failure",
    "EvidenceLimits",
    "EvidenceValidationError",
    "FailureEvidence",
    "RepairRequest",
    "SourceLocation",
    "StackFrame",
]
