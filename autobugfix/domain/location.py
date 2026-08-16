"""Serializable models for evidence-based source localization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LocalizationLimits:
    """Explicit bounds for one localization operation."""

    max_candidates: int = 20
    max_files_considered: int = 50
    max_ast_files: int = 20
    max_evidence_frames: int = 50

    def __post_init__(self) -> None:
        for name in ("max_candidates", "max_files_considered", "max_ast_files", "max_evidence_frames"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class LocalizationEvidence:
    """Factual or explicitly named ranking signals for one candidate."""

    sources: tuple[str, ...] = ()
    score_components: tuple[tuple[str, int], ...] = ()
    rank_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": list(self.sources),
            "score_components": {name: value for name, value in self.score_components},
            "rank_reason": self.rank_reason,
        }


@dataclass(frozen=True)
class AstParseFailure:
    """A bounded diagnostic for a repository file that is not valid Python."""

    relative_path: str
    line: int | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"relative_path": self.relative_path, "line": self.line, "message": self.message}


@dataclass(frozen=True)
class LocalizationCandidate:
    relative_path: str
    line_start: int
    line_end: int
    enclosing_function: str | None
    enclosing_class: str | None
    evidence: LocalizationEvidence
    rank: int
    ast_available: bool = True
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "enclosing_function": self.enclosing_function,
            "enclosing_class": self.enclosing_class,
            "evidence": self.evidence.to_dict(),
            "rank": self.rank,
            "ast_available": self.ast_available,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class LocalizationResult:
    candidates: tuple[LocalizationCandidate, ...] = ()
    diagnostics: tuple[AstParseFailure | str, ...] = ()
    considered_files: tuple[str, ...] = ()
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "diagnostics": [item.to_dict() if isinstance(item, AstParseFailure) else item for item in self.diagnostics],
            "considered_files": list(self.considered_files),
            "truncated": self.truncated,
            "root_cause_confirmed": False,
        }


__all__ = [
    "AstParseFailure",
    "LocalizationCandidate",
    "LocalizationEvidence",
    "LocalizationLimits",
    "LocalizationResult",
]
