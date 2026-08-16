import json
import subprocess
from pathlib import Path

import pytest

from autobugfix.cli import main
from autobugfix.workspace import (
    NotGitRepositoryError,
    PathOutsideWorkspaceError,
    RepositoryReadError,
    RepositoryWorkspace,
    UnsupportedFileError,
    WorkspaceLimitError,
    WorkspacePathError,
    WorkspacePolicy,
)


def run_git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    return result.stdout.strip()


def make_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "project"
    (repository / "src").mkdir(parents=True)
    (repository / "src" / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repository / "src" / "z.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repository / "src" / "binary.py").write_bytes(b"not text\x00\x01")
    (repository / "src" / "invalid.py").write_bytes(b"\xff\xfe")
    (repository / "notes.txt").write_text("not Python\n", encoding="utf-8")
    (repository / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    (repository / "private.pem").write_text("PRIVATE KEY\n", encoding="utf-8")
    for directory in (".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist"):
        (repository / directory).mkdir()
        (repository / directory / "ignored.py").write_text("ignored = True\n", encoding="utf-8")
    run_git(repository, "init")
    run_git(repository, "config", "user.email", "tests@example.invalid")
    run_git(repository, "config", "user.name", "Auto-Bug-Fix Tests")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "fixture")
    return repository


def test_repository_root_nested_path_file_and_head(tmp_path):
    repository = make_repository(tmp_path)
    expected_head = run_git(repository, "rev-parse", "HEAD")

    workspace = RepositoryWorkspace.open(repository / "src" / "main.py")

    assert workspace.root == repository.resolve()
    assert workspace.base_commit == expected_head
    assert workspace.state.is_git_repository is True
    assert workspace.state.is_dirty is False
    assert workspace.relative_path(repository / "src" / "main.py") == "src/main.py"


def test_non_git_and_missing_paths_are_actionable(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()

    with pytest.raises(NotGitRepositoryError):
        RepositoryWorkspace.open(plain)
    with pytest.raises(WorkspacePathError):
        RepositoryWorkspace.open(tmp_path / "missing")


def test_git_state_reports_dirty_repository(tmp_path):
    repository = make_repository(tmp_path)
    (repository / "dirty.py").write_text("dirty = True\n", encoding="utf-8")

    workspace = RepositoryWorkspace.open(repository)

    assert workspace.state.is_dirty is True


def test_git_state_reports_detached_head(tmp_path):
    repository = make_repository(tmp_path)
    run_git(repository, "checkout", "--detach", "HEAD")

    workspace = RepositoryWorkspace.open(repository)

    assert workspace.state.detached_head is True
    assert workspace.state.branch is None


def test_enumeration_is_sorted_python_only_and_ignores_unsafe_entries(tmp_path):
    repository = make_repository(tmp_path)
    workspace = RepositoryWorkspace.open(repository)

    files = workspace.list_source_files()

    assert [item.relative_path for item in files] == ["src/main.py", "src/z.py"]
    summary = workspace.summary()
    assert summary.eligible_python_files == 2
    assert summary.ignored_entries >= 10


def test_additional_ignore_patterns_are_supported(tmp_path):
    repository = make_repository(tmp_path)
    (repository / "src" / "custom_ignored.py").write_text("ignored = True\n", encoding="utf-8")
    workspace = RepositoryWorkspace.open(
        repository,
        WorkspacePolicy(additional_ignore_patterns=("src/custom_ignored.py",)),
    )

    assert "src/custom_ignored.py" not in [item.relative_path for item in workspace.list_source_files()]


def test_read_text_is_utf8_bounded_and_read_only(tmp_path):
    repository = make_repository(tmp_path)
    before = run_git(repository, "status", "--porcelain", "--untracked-files=all")
    workspace = RepositoryWorkspace.open(repository)

    assert workspace.read_text("src/main.py") == "VALUE = 1\n"
    with pytest.raises(UnsupportedFileError):
        workspace.read_text(".env")
    with pytest.raises(RepositoryReadError):
        workspace.read_text("src/invalid.py")

    after = run_git(repository, "status", "--porcelain", "--untracked-files=all")
    assert after == before


def test_containment_rejects_traversal_absolute_paths_and_similar_siblings(tmp_path):
    repository = make_repository(tmp_path)
    sibling = tmp_path / "project-evil"
    sibling.mkdir()
    (sibling / "evil.py").write_text("evil = True\n", encoding="utf-8")
    workspace = RepositoryWorkspace.open(repository)

    for path in ("../outside.py", "..\\outside.py", str(sibling / "evil.py")):
        with pytest.raises(PathOutsideWorkspaceError):
            workspace.read_text(path)
    with pytest.raises(PathOutsideWorkspaceError):
        workspace.read_text("C:\\Windows\\System32\\drivers\\etc\\hosts")
    with pytest.raises(PathOutsideWorkspaceError):
        workspace.read_text("/path/outside.py")
    with pytest.raises(PathOutsideWorkspaceError):
        workspace.relative_path(sibling / "evil.py")


def test_size_limits_fail_explicitly_and_warn_during_enumeration(tmp_path):
    repository = make_repository(tmp_path)
    policy = WorkspacePolicy(max_file_size=4)
    workspace = RepositoryWorkspace.open(repository, policy)

    with pytest.raises(WorkspaceLimitError):
        workspace.read_text("src/main.py")
    summary = workspace.summary()
    assert summary.eligible_python_files == 0
    assert any("oversized" in warning for warning in summary.warnings)


def test_file_count_limit_fails_explicitly(tmp_path):
    repository = make_repository(tmp_path)
    policy = WorkspacePolicy(max_source_files=1)

    with pytest.raises(WorkspaceLimitError):
        RepositoryWorkspace.open(repository, policy).list_source_files()


def test_symlink_policy_handles_internal_and_external_targets(tmp_path):
    repository = make_repository(tmp_path)
    external = tmp_path / "outside.py"
    external.write_text("outside = True\n", encoding="utf-8")
    try:
        (repository / "src" / "internal.py").symlink_to("main.py")
        (repository / "src" / "external.py").symlink_to(external)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation is unavailable in this environment: {exc}")

    workspace = RepositoryWorkspace.open(repository)
    paths = [item.relative_path for item in workspace.list_source_files()]

    assert "src/internal.py" in paths
    assert "src/external.py" not in paths
    assert workspace.read_text("src/internal.py") == "VALUE = 1\n"
    with pytest.raises(PathOutsideWorkspaceError):
        workspace.read_text("src/external.py")


def test_cli_inspect_repo_json_and_invalid_repository(tmp_path, capsys):
    repository = make_repository(tmp_path)

    assert main(["inspect-repo", str(repository), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["eligible_python_files"] == 2
    assert output["root"] == str(repository.resolve())

    assert main(["inspect-repo", str(tmp_path / "not-a-repository")]) == 2
    assert "does not exist" in capsys.readouterr().err
