"""Serializable, bounded failure evidence models.

The models in this module contain observations only.  They do not infer a
root cause, execute log content, or contact an external provider.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from typing import Any, Mapping


@dataclass(frozen=True)
class EvidenceLimits:
    """Input limits applied before parsing or serialization."""

    max_input_bytes: int = 64 * 1024
    max_lines: int = 2_000
    max_issue_text_bytes: int = 32 * 1024
    max_excerpt_chars: int = 500

    def __post_init__(self) -> None:
        if any(value <= 0 for value in asdict(self).values()):
            raise ValueError("evidence limits must be positive")


@dataclass(frozen=True)
class SourceLocation:
    """A factual source location extracted from failure text."""

    file: str
    line: int | None = None
    column: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceLocation":
        return cls(
            file=str(value["file"]),
            line=_optional_int(value.get("line")),
            column=_optional_int(value.get("column")),
        )


@dataclass(frozen=True)
class StackFrame:
    """One ordered traceback frame, with no root-cause interpretation."""

    location: SourceLocation
    function: str | None = None
    message: str | None = None
    excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location.to_dict(),
            "function": self.function,
            "message": self.message,
            "excerpt": self.excerpt,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StackFrame":
        return cls(
            location=SourceLocation.from_dict(value["location"]),
            function=_optional_str(value.get("function")),
            message=_optional_str(value.get("message")),
            excerpt=_optional_str(value.get("excerpt")),
        )


@dataclass(frozen=True)
class FailureEvidence:
    """Bounded observations extracted from one failure input."""

    source: str
    raw_log: str
    frames: tuple[StackFrame, ...] = dataclass_field(default_factory=tuple)
    message: str | None = None
    excerpts: tuple[str, ...] = dataclass_field(default_factory=tuple)
    parser: str = "none"
    parser_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "raw_log": self.raw_log,
            "frames": [frame.to_dict() for frame in self.frames],
            "message": self.message,
            "excerpts": list(self.excerpts),
            "parser": self.parser,
            "parser_confidence": self.parser_confidence,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FailureEvidence":
        return cls(
            source=str(value["source"]),
            raw_log=str(value["raw_log"]),
            frames=tuple(StackFrame.from_dict(item) for item in value.get("frames", [])),
            message=_optional_str(value.get("message")),
            excerpts=tuple(str(item) for item in value.get("excerpts", [])),
            parser=str(value.get("parser", "none")),
            parser_confidence=float(value.get("parser_confidence", 0.0)),
        )


@dataclass(frozen=True)
class RepairRequest:
    """A normalized repair input; issue text remains separate from observed facts."""

    evidence: FailureEvidence
    issue_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"evidence": self.evidence.to_dict(), "issue_text": self.issue_text}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RepairRequest":
        return cls(
            evidence=FailureEvidence.from_dict(value["evidence"]),
            issue_text=_optional_str(value.get("issue_text")),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_json(cls, value: str) -> "RepairRequest":
        parsed = json.loads(value)
        if not isinstance(parsed, Mapping):
            raise ValueError("repair request JSON must contain an object")
        return cls.from_dict(parsed)


@dataclass(frozen=True)
class EvidenceValidationError(ValueError):
    """Structured validation failure for hostile or unsupported input."""

    code: str
    message: str
    field: str = "raw_log"
    details: Mapping[str, Any] = dataclass_field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "field": self.field,
                "message": self.message,
                "details": dict(self.details),
            }
        }


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
