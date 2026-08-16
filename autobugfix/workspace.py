"""Safe, inspection-only access to an existing local Git repository."""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath


class WorkspaceError(Exception):
    """Base class for actionable repository workspace failures."""


class WorkspacePathError(WorkspaceError):
    """The requested workspace path does not exist or is not a directory/file."""


class NotGitRepositoryError(WorkspaceError):
    """The selected path is not inside an existing Git repository."""


class PathOutsideWorkspaceError(WorkspaceError):
    """A requested path would escape the resolved repository root."""


class UnsupportedFileError(WorkspaceError):
    """A file is excluded by the workspace's source or sensitive-file policy."""


class WorkspaceLimitError(WorkspaceError):
    """A configured file-size or enumeration limit was exceeded."""


class RepositoryReadError(WorkspaceError):
    """A permitted repository file could not be read as strict UTF-8 text."""


@dataclass(frozen=True)
class WorkspacePolicy:
    """Centralized safety limits and additional ignore patterns."""

    max_file_size: int = 1 * 1024 * 1024
    max_source_files: int = 10_000
    additional_ignore_patterns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_file_size <= 0:
            raise ValueError("max_file_size must be positive")
        if self.max_source_files <= 0:
            raise ValueError("max_source_files must be positive")


@dataclass(frozen=True)
class RepositoryState:
    """Git state observed without changing repository state."""

    is_git_repository: bool
    base_commit: str | None
    branch: str | None
    detached_head: bool
    is_dirty: bool


@dataclass(frozen=True)
class RepositoryFile:
    """A source file eligible for bounded inspection."""

    relative_path: str
    size: int


@dataclass(frozen=True)
class WorkspaceSummary:
    """Small, serializable result for the inspect-repo CLI."""

    root: str
    git_root: str
    base_commit: str | None
    branch: str | None
    detached_head: bool
    is_dirty: bool
    eligible_python_files: int
    ignored_entries: int
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible summary data."""

        return {
            "base_commit": self.base_commit,
            "branch": self.branch,
            "detached_head": self.detached_head,
            "eligible_python_files": self.eligible_python_files,
            "git_root": self.git_root,
            "ignored_entries": self.ignored_entries,
            "is_dirty": self.is_dirty,
            "root": self.root,
            "warnings": list(self.warnings),
        }


_IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "env",
        "htmlcov",
        "node_modules",
        "site-packages",
        "venv",
    }
)
_SENSITIVE_NAMES = (".env", ".env.*", "*.pem", "*.key", "id_rsa", "id_ed25519")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
_GIT_TIMEOUT_SECONDS = 5
_GIT_INSPECTION_OPTIONS = (
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.untrackedCache=false",
    "--no-optional-locks",
)


class RepositoryWorkspace:
    """Read-only, contained view of an existing local Git repository."""

    def __init__(self, root: Path, state: RepositoryState, policy: WorkspacePolicy) -> None:
        self.root = root
        self.base_commit = state.base_commit
        self.state = state
        self.policy = policy
        self._warnings: list[str] = []

    @classmethod
    def open(
        cls, path: str | os.PathLike[str], policy: WorkspacePolicy | None = None
    ) -> "RepositoryWorkspace":
        """Open an existing repository from its root, nested path, or file."""

        candidate = Path(path).expanduser()
        if not candidate.exists():
            raise WorkspacePathError(f"workspace path does not exist: {candidate}")
        start = candidate.parent if candidate.is_file() else candidate
        try:
            start = start.resolve(strict=True)
        except OSError as exc:
            raise WorkspacePathError(f"cannot resolve workspace path: {candidate}") from exc

        git_root_text = cls._run_git(start, "rev-parse", "--show-toplevel").strip()
        if not git_root_text:
            raise NotGitRepositoryError(f"not inside a Git repository: {candidate}")
        try:
            root = Path(git_root_text).resolve(strict=True)
        except OSError as exc:
            raise NotGitRepositoryError(f"Git repository root is unavailable: {candidate}") from exc

        base_commit = cls._git_value(root, "rev-parse", "HEAD", allow_failure=True)
        branch = cls._git_value(root, "symbolic-ref", "--quiet", "--short", "HEAD", allow_failure=True)
        status = cls._run_git(
            root,
            "status",
            "--porcelain",
            "--untracked-files=normal",
            "--ignore-submodules=all",
        )
        state = RepositoryState(
            is_git_repository=True,
            base_commit=base_commit or None,
            branch=branch or None,
            detached_head=not bool(branch),
            is_dirty=bool(status.strip()),
        )
        return cls(root, state, policy or WorkspacePolicy())

    @staticmethod
    def _run_git(cwd: Path, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *_GIT_INSPECTION_OPTIONS, *args],
                cwd=cwd,
                capture_output=True,
                check=False,
                shell=False,
                text=True,
                timeout=_GIT_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise NotGitRepositoryError(f"unable to inspect Git repository at {cwd}") from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
            raise NotGitRepositoryError(f"Git inspection failed at {cwd}: {detail}")
        return result.stdout

    @classmethod
    def _git_value(cls, cwd: Path, *args: str, allow_failure: bool = False) -> str:
        try:
            return cls._run_git(cwd, *args).strip()
        except NotGitRepositoryError:
            if allow_failure:
                return ""
            raise

    @property
    def is_git_repository(self) -> bool:
        return self.state.is_git_repository

    def relative_path(self, path: str | os.PathLike[str]) -> str:
        """Return a safe repository-relative POSIX path."""

        raw = os.fspath(path)
        if "\x00" in raw:
            raise PathOutsideWorkspaceError("repository paths may not contain NUL bytes")
        portable = raw.replace("\\", "/")
        if PurePosixPath(portable).is_absolute() or PureWindowsPath(raw).is_absolute() or _WINDOWS_DRIVE.match(raw):
            if _WINDOWS_DRIVE.match(raw) and os.name != "nt":
                raise PathOutsideWorkspaceError(f"Windows absolute path is not valid here: {raw}")
            lexical_candidate = Path(os.path.abspath(os.fspath(Path(raw).expanduser())))
            self._assert_contained(lexical_candidate)
            self._assert_contained(lexical_candidate.resolve(strict=False))
            return lexical_candidate.relative_to(self.root).as_posix()
        relative = PurePosixPath(portable)
        if any(part == ".." for part in relative.parts):
            raise PathOutsideWorkspaceError(f"path escapes repository root: {raw}")
        if relative == PurePosixPath(".") or not relative.parts:
            raise UnsupportedFileError("a repository-relative file path is required")
        lexical_candidate = self.root.joinpath(*relative.parts)
        self._assert_contained(lexical_candidate.resolve(strict=False))
        return relative.as_posix()

    def read_text(self, relative_path: str | os.PathLike[str]) -> str:
        """Read one approved UTF-8 source file without executing it."""

        raw = os.fspath(relative_path)
        if PurePosixPath(raw.replace("\\", "/")).is_absolute() or PureWindowsPath(raw).is_absolute() or _WINDOWS_DRIVE.match(raw):
            raise PathOutsideWorkspaceError("read_text accepts repository-relative paths only")
        safe_relative = self.relative_path(relative_path)
        lexical_path = self.root.joinpath(*PurePosixPath(safe_relative).parts)
        resolved_path = self._validate_file_pair(lexical_path, safe_relative)
        return self._read_bounded_text(resolved_path, safe_relative)

    def list_source_files(self) -> list[RepositoryFile]:
        """Enumerate bounded, deterministic Python source files."""

        files, warnings, _ = self._scan()
        self._warnings = warnings
        return files

    def summary(self) -> WorkspaceSummary:
        """Return repository metadata and a bounded source enumeration summary."""

        files, warnings, ignored_entries = self._scan()
        self._warnings = warnings
        return WorkspaceSummary(
            root=str(self.root),
            git_root=str(self.root),
            base_commit=self.state.base_commit,
            branch=self.state.branch,
            detached_head=self.state.detached_head,
            is_dirty=self.state.is_dirty,
            eligible_python_files=len(files),
            ignored_entries=ignored_entries,
            warnings=tuple(warnings),
        )

    def _scan(self) -> tuple[list[RepositoryFile], list[str], int]:
        files: list[RepositoryFile] = []
        warnings: list[str] = []
        ignored_entries = 0
        for current_root, directories, names in os.walk(self.root, topdown=True, followlinks=False):
            current = Path(current_root)
            kept_directories: list[str] = []
            for name in sorted(directories):
                relative = (current / name).relative_to(self.root).as_posix()
                if self._is_ignored_directory(name, relative) or (current / name).is_symlink():
                    ignored_entries += 1
                else:
                    kept_directories.append(name)
            directories[:] = kept_directories
            for name in sorted(names):
                path = current / name
                relative = path.relative_to(self.root).as_posix()
                if self._is_ignored_file(name, relative):
                    ignored_entries += 1
                    continue
                if path.suffix.lower() != ".py":
                    ignored_entries += 1
                    continue
                try:
                    resolved_path = self._validate_file_pair(path, relative)
                except PathOutsideWorkspaceError:
                    ignored_entries += 1
                    warnings.append(f"ignored symlink outside workspace: {relative}")
                    continue
                except UnsupportedFileError as exc:
                    ignored_entries += 1
                    warnings.append(str(exc))
                    continue
                try:
                    text = self._read_bounded_text(resolved_path, relative)
                except WorkspaceLimitError as exc:
                    ignored_entries += 1
                    warnings.append(str(exc))
                    continue
                except (RepositoryReadError, UnsupportedFileError) as exc:
                    ignored_entries += 1
                    warnings.append(str(exc))
                    continue
                size = len(text.encode("utf-8"))
                files.append(RepositoryFile(relative_path=relative, size=size))
                if len(files) > self.policy.max_source_files:
                    raise WorkspaceLimitError(
                        f"repository exceeds max_source_files ({self.policy.max_source_files})"
                    )
        files.sort(key=lambda item: item.relative_path)
        return files, sorted(set(warnings)), ignored_entries

    def _assert_contained(self, candidate: Path) -> None:
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise PathOutsideWorkspaceError(
                f"path is outside repository root {self.root}: {candidate}"
            ) from exc

    def _validate_file_pair(self, lexical_path: Path, lexical_relative: str) -> Path:
        """Validate both the user-visible path and its resolved target."""

        if self._is_ignored_directory_path(lexical_relative) or self._is_ignored_file(
            lexical_path.name, lexical_relative
        ):
            raise UnsupportedFileError(f"file is excluded by policy: {lexical_relative}")
        if lexical_path.suffix.lower() != ".py":
            raise UnsupportedFileError(
                f"only UTF-8 Python source files are readable: {lexical_relative}"
            )
        if not lexical_path.exists() or not lexical_path.is_file():
            raise RepositoryReadError(f"repository file does not exist: {lexical_relative}")
        try:
            resolved_path = lexical_path.resolve(strict=True)
        except OSError as exc:
            raise RepositoryReadError(f"cannot resolve repository file: {lexical_relative}") from exc
        self._assert_contained(resolved_path)
        resolved_relative = resolved_path.relative_to(self.root).as_posix()
        if self._is_ignored_directory_path(resolved_relative) or self._is_ignored_file(
            resolved_path.name, resolved_relative
        ):
            raise UnsupportedFileError(
                f"resolved target is excluded by policy: {lexical_relative}"
            )
        if resolved_path.suffix.lower() != ".py":
            raise UnsupportedFileError(
                f"resolved target is not Python source: {lexical_relative}"
            )
        if not resolved_path.is_file():
            raise RepositoryReadError(f"repository file is not regular: {lexical_relative}")
        return resolved_path

    def _symlink_is_contained(self, path: Path) -> bool:
        try:
            target = path.resolve(strict=True)
        except OSError:
            return False
        try:
            target.relative_to(self.root)
        except ValueError:
            return False
        return True

    def _read_bounded_bytes(self, path: Path, relative: str) -> bytes:
        """Read at most max_file_size plus one byte from a source file."""

        try:
            with path.open("rb") as handle:
                data = handle.read(self.policy.max_file_size + 1)
        except OSError as exc:
            raise RepositoryReadError(f"cannot read repository file: {relative}") from exc
        if len(data) > self.policy.max_file_size:
            raise WorkspaceLimitError(
                f"file exceeds max_file_size ({self.policy.max_file_size} bytes): {relative}"
            )
        if b"\x00" in data:
            raise UnsupportedFileError(f"file is not text: {relative}")
        return data

    def _read_bounded_text(self, path: Path, relative: str) -> str:
        data = self._read_bounded_bytes(path, relative)
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RepositoryReadError(f"cannot read UTF-8 source file: {relative}") from exc

    def _is_ignored_directory_path(self, relative: str) -> bool:
        parts = PurePosixPath(relative).parts
        for index, part in enumerate(parts[:-1]):
            prefix = PurePosixPath(*parts[: index + 1]).as_posix()
            if part in _IGNORED_DIRECTORIES or self._matches_additional_pattern(part, prefix):
                return True
        return False

    def _is_ignored_directory(self, name: str, relative: str) -> bool:
        return name in _IGNORED_DIRECTORIES or self._matches_additional_pattern(name, relative)

    def _is_ignored_file(self, name: str, relative: str) -> bool:
        return any(fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(relative, pattern) for pattern in _SENSITIVE_NAMES) or self._matches_additional_pattern(name, relative)

    def _matches_additional_pattern(self, name: str, relative: str) -> bool:
        return any(
            fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(relative, pattern)
            for pattern in self.policy.additional_ignore_patterns
        )


def format_summary(summary: WorkspaceSummary) -> str:
    """Render a concise human-readable inspection summary."""

    head = summary.base_commit or "unavailable"
    state = "dirty" if summary.is_dirty else "clean"
    branch = "detached HEAD" if summary.detached_head else (summary.branch or "unknown branch")
    lines = [
        f"Repository root: {summary.root}",
        f"Git root: {summary.git_root}",
        f"HEAD: {head}",
        f"State: {state} ({branch})",
        f"Eligible Python files: {summary.eligible_python_files}",
        f"Ignored entries: {summary.ignored_entries}",
    ]
    if summary.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in summary.warnings)
    return "\n".join(lines)
