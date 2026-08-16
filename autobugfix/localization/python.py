"""Evidence-based, Python-only fault localization without code execution."""

from __future__ import annotations

import ast
import posixpath
from dataclasses import dataclass, replace
from pathlib import PurePosixPath, PureWindowsPath

from ..domain.location import (
    AstParseFailure,
    LocalizationCandidate,
    LocalizationEvidence,
    LocalizationLimits,
    LocalizationResult,
)
from ..evidence import FailureEvidence, StackFrame
from ..workspace import RepositoryWorkspace, WorkspaceError


@dataclass(frozen=True)
class _Symbol:
    kind: str
    name: str
    line_start: int
    line_end: int
    function: str | None
    class_name: str | None


class PythonFaultLocalizer:
    """Map observed traceback frames to bounded repository-local AST locations."""

    def __init__(self, workspace: RepositoryWorkspace, limits: LocalizationLimits | None = None) -> None:
        self.workspace = workspace
        self.limits = limits or LocalizationLimits()

    def localize(self, evidence: FailureEvidence) -> LocalizationResult:
        frames = evidence.frames[: self.limits.max_evidence_frames]
        files = tuple(item.relative_path for item in self.workspace.list_source_files())
        file_set = set(files)
        mappings: list[tuple[int, StackFrame, str, tuple[str, ...]]] = []
        diagnostics: list[AstParseFailure | str] = []
        for index, frame in enumerate(frames):
            mapped, signals = self._map_frame(frame, files)
            if mapped is None:
                diagnostics.append(f"unmatched traceback frame {index}: {frame.location.file}")
                continue
            if mapped not in file_set:
                continue
            mappings.append((index, frame, mapped, signals))
        relevant_files = sorted({item[2] for item in mappings})[: self.limits.max_files_considered]
        ast_index: dict[str, tuple[_Symbol, ...]] = {}
        for relative_path in relevant_files[: self.limits.max_ast_files]:
            try:
                source = self.workspace.read_text(relative_path)
                tree = ast.parse(source, filename=relative_path)
            except SyntaxError as exc:
                diagnostics.append(AstParseFailure(relative_path, exc.lineno, exc.msg))
                continue
            except WorkspaceError as exc:
                diagnostics.append(f"unable to index {relative_path}: {exc}")
                continue
            ast_index[relative_path] = tuple(_symbols(tree))
        candidates: list[LocalizationCandidate] = []
        for index, frame, relative_path, signals in mappings:
            if relative_path not in relevant_files:
                continue
            line = frame.location.line or 1
            symbols = ast_index.get(relative_path)
            symbol = _narrowest_symbol(symbols or (), line) if symbols is not None else None
            sources = list(signals)
            components = {"repository_local_frame": 100, "frame_position": index}
            if "traceback_exact_path" in sources:
                components["traceback_exact_path"] = 40
            elif "traceback_absolute_suffix" in sources:
                components["traceback_absolute_suffix"] = 25
            elif "traceback_unique_suffix" in sources:
                components["traceback_unique_suffix"] = 10
            if frame.location.line is not None:
                sources.append("traceback_line")
                components["traceback_line"] = 15
            if frame.function and symbol and _leaf_name(symbol.function) == frame.function:
                sources.append("function_name_match")
                components["function_name_match"] = 10
            if symbol:
                sources.append("ast_symbol_span")
                components["ast_symbol_span"] = 20
                start, end = symbol.line_start, symbol.line_end
                function, class_name = symbol.function, symbol.class_name
            else:
                start = end = max(1, line)
                function = class_name = None
            candidates.append(
                LocalizationCandidate(
                    relative_path=relative_path,
                    line_start=start,
                    line_end=end,
                    enclosing_function=function,
                    enclosing_class=class_name,
                    evidence=LocalizationEvidence(
                        sources=tuple(dict.fromkeys(sources)),
                        score_components=tuple(sorted(components.items())),
                        rank_reason="; ".join(dict.fromkeys(sources)),
                    ),
                    rank=0,
                    ast_available=symbols is not None,
                    diagnostics=() if symbols is not None else ("AST structure unavailable",),
                )
            )
        ordered = sorted(
            candidates,
            key=lambda item: (-sum(value for _, value in item.evidence.score_components), item.relative_path, item.line_start, item.line_end),
        )
        ranked = tuple(
            replace(candidate, rank=rank)
            for rank, candidate in enumerate(ordered[: self.limits.max_candidates], 1)
        )
        return LocalizationResult(
            candidates=ranked,
            diagnostics=tuple(diagnostics),
            considered_files=tuple(relevant_files[: self.limits.max_ast_files]),
            truncated=len(ordered) > self.limits.max_candidates or len(relevant_files) > self.limits.max_ast_files,
        )

    def _map_frame(self, frame: StackFrame, files: tuple[str, ...]) -> tuple[str | None, tuple[str, ...]]:
        raw = frame.location.file.replace("\\", "/")
        if ".." in PurePosixPath(raw).parts:
            return None, ()
        normalized = posixpath.normpath(raw)
        if not PurePosixPath(normalized).is_absolute() and not PureWindowsPath(raw).is_absolute():
            if normalized in files:
                return normalized, ("traceback_exact_path",)
        matches = [relative for relative in files if normalized.endswith("/" + relative) or normalized == relative]
        if len(matches) == 1:
            return matches[0], ("traceback_absolute_suffix",) if PureWindowsPath(raw).is_absolute() or PurePosixPath(normalized).is_absolute() else ("traceback_unique_suffix",)
        basename = PurePosixPath(normalized).name
        matches = [relative for relative in files if PurePosixPath(relative).name == basename]
        if len(matches) == 1:
            return matches[0], ("traceback_unique_suffix",)
        return None, ()


def _symbols(tree: ast.Module) -> list[_Symbol]:
    result: list[_Symbol] = []

    def visit(body: list[ast.stmt], function: str | None, class_name: str | None) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{function}.{node.name}" if function else node.name
                result.append(_make_symbol(node, "function", name, name, class_name))
                visit(node.body, name, class_name)
            elif isinstance(node, ast.ClassDef):
                name = f"{class_name}.{node.name}" if class_name else node.name
                result.append(_make_symbol(node, "class", name, function, name))
                visit(node.body, function, name)

    visit(tree.body, None, None)
    return result


def _make_symbol(node: ast.AST, kind: str, name: str, function: str | None, class_name: str | None) -> _Symbol:
    node_line = int(getattr(node, "lineno", 1))
    decorators = getattr(node, "decorator_list", ())
    starts = [int(getattr(item, "lineno", node_line)) for item in decorators]
    end_line = int(getattr(node, "end_lineno", node_line))
    return _Symbol(kind, name, min([node_line, *starts]), end_line, function, class_name)


def _narrowest_symbol(symbols: tuple[_Symbol, ...], line: int) -> _Symbol | None:
    matches = [symbol for symbol in symbols if symbol.line_start <= line <= symbol.line_end]
    return min(matches, key=lambda symbol: (symbol.line_end - symbol.line_start, symbol.line_start, symbol.name), default=None)


def _leaf_name(value: str | None) -> str | None:
    return value.rsplit(".", 1)[-1] if value else None


__all__ = ["PythonFaultLocalizer"]
