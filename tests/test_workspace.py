import json
import os
import shlex
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
    assert workspace.state.is_dirty is None
    assert workspace.relative_path(repository / "src" / "main.py") == "src/main.py"


def test_non_git_and_missing_paths_are_actionable(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()

    with pytest.raises(NotGitRepositoryError):
        RepositoryWorkspace.open(plain)
    with pytest.raises(WorkspacePathError):
        RepositoryWorkspace.open(tmp_path / "missing")


def test_git_state_reports_unknown_worktree_state(tmp_path):
    repository = make_repository(tmp_path)
    assert RepositoryWorkspace.open(repository).state.is_dirty is None
    (repository / "dirty.py").write_text("dirty = True\n", encoding="utf-8")

    workspace = RepositoryWorkspace.open(repository)

    assert workspace.state.is_dirty is None


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

    expected = (repository / "src" / "main.py").read_bytes().decode("utf-8")
    assert workspace.read_text("src/main.py") == expected
    with pytest.raises(UnsupportedFileError):
        workspace.read_text(".env")
    with pytest.raises(RepositoryReadError):
        workspace.read_text("src/invalid.py")

    after = run_git(repository, "status", "--porcelain", "--untracked-files=all")
    assert after == before


def test_inspection_does_not_rewrite_index_after_tracked_mtime_change(tmp_path):
    repository = make_repository(tmp_path)
    index = repository / ".git" / "index"
    tracked = repository / "src" / "main.py"
    index_before = index.read_bytes()
    index_stat_before = index.stat()
    tracked_stat = tracked.stat()
    os.utime(
        tracked,
        ns=(tracked_stat.st_atime_ns, tracked_stat.st_mtime_ns + 10_000_000),
    )

    RepositoryWorkspace.open(repository).summary()

    index_stat_after = index.stat()
    assert index.read_bytes() == index_before
    assert index_stat_after.st_mtime_ns == index_stat_before.st_mtime_ns
    assert index_stat_after.st_size == index_stat_before.st_size


@pytest.mark.skipif(os.name == "nt", reason="POSIX clean-filter test")
def test_repository_clean_filter_is_not_executed_during_inspection(tmp_path):
    repository = make_repository(tmp_path)
    attributes = repository / ".gitattributes"
    attributes.write_text("*.py filter=evil\n", encoding="utf-8")
    run_git(repository, "add", ".gitattributes")
    run_git(repository, "commit", "-m", "configure filter attributes")
    marker = tmp_path / "clean-filter-ran"
    filter_command = tmp_path / "evil-clean-filter.sh"
    filter_command.write_text(
        "#!/bin/sh\n"
        f"printf ran > {shlex.quote(str(marker))}\n"
        "cat\n",
        encoding="utf-8",
    )
    filter_command.chmod(0o755)
    run_git(repository, "config", "filter.evil.clean", str(filter_command))
    run_git(repository, "config", "filter.evil.smudge", "cat")
    (repository / "src" / "main.py").write_text("VALUE = 999\n", encoding="utf-8")

    summary = RepositoryWorkspace.open(repository).summary()

    assert summary.is_dirty is None
    assert not marker.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX fsmonitor hook test")
def test_repository_fsmonitor_command_is_not_executed(tmp_path):
    repository = make_repository(tmp_path)
    marker = tmp_path / "fsmonitor-ran"
    hook = tmp_path / "fsmonitor-hook.sh"
    hook.write_text(
        "#!/bin/sh\n"
        f"printf ran > {shlex.quote(str(marker))}\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)
    run_git(repository, "config", "core.fsmonitor", str(hook))

    RepositoryWorkspace.open(repository).summary()

    assert not marker.exists()


def test_oversized_source_uses_bounded_reads(monkeypatch, tmp_path):
    repository = make_repository(tmp_path)
    policy = WorkspacePolicy(max_file_size=4)
    workspace = RepositoryWorkspace.open(repository, policy)

    def fail_if_unbounded_read(_path):
        pytest.fail("Path.read_bytes() must not be used for source inspection")

    monkeypatch.setattr(Path, "read_bytes", fail_if_unbounded_read)
    summary = workspace.summary()

    assert summary.eligible_python_files == 0
    with pytest.raises(WorkspaceLimitError):
        workspace.read_text("src/main.py")


def test_invalid_utf8_after_byte_8192_is_rejected_consistently(tmp_path):
    repository = make_repository(tmp_path)
    late_invalid = repository / "src" / "late_invalid.py"
    late_invalid.write_bytes(b"a" * 9000 + b"\xff")
    workspace = RepositoryWorkspace.open(repository)

    assert "src/late_invalid.py" not in [
        item.relative_path for item in workspace.list_source_files()
    ]
    with pytest.raises(RepositoryReadError):
        workspace.read_text("src/late_invalid.py")


def test_internal_symlink_targets_must_pass_target_and_lexical_policies(tmp_path):
    repository = make_repository(tmp_path)
    source = repository / "src"
    try:
        (source / "env_alias.py").symlink_to(Path("..") / ".env")
        (source / "key_alias.py").symlink_to(Path("..") / "private.pem")
        (source / "custom_alias.py").symlink_to("main.py")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation is unavailable in this environment: {exc}")
    workspace = RepositoryWorkspace.open(
        repository,
        WorkspacePolicy(additional_ignore_patterns=("src/custom_alias.py",)),
    )

    paths = [item.relative_path for item in workspace.list_source_files()]
    assert "src/env_alias.py" not in paths
    assert "src/key_alias.py" not in paths
    assert "src/custom_alias.py" not in paths
    for alias in ("src/env_alias.py", "src/key_alias.py", "src/custom_alias.py"):
        with pytest.raises(UnsupportedFileError):
            workspace.read_text(alias)


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
    assert any("exceeds max_file_size" in warning for warning in summary.warnings)


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
    assert workspace.relative_path("src/internal.py") == "src/internal.py"
    assert workspace.relative_path(repository / "src" / "internal.py") == "src/internal.py"
    assert workspace.read_text("src/internal.py") == "VALUE = 1\n"
    with pytest.raises(PathOutsideWorkspaceError):
        workspace.read_text("src/external.py")


def test_cli_inspect_repo_json_and_invalid_repository(tmp_path, capsys):
    repository = make_repository(tmp_path)

    assert main(["inspect-repo", str(repository), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["eligible_python_files"] == 2
    assert output["is_dirty"] is None
    assert output["root"] == str(repository.resolve())

    assert main(["inspect-repo", str(repository)]) == 0
    assert "Worktree state: unknown" in capsys.readouterr().out

    assert main(["inspect-repo", str(tmp_path / "not-a-repository")]) == 2
    assert "does not exist" in capsys.readouterr().err
