import subprocess
from pathlib import Path

from autobugfix.domain.location import LocalizationLimits
from autobugfix.evidence import FailureEvidence, SourceLocation, StackFrame
from autobugfix.localization import PythonFaultLocalizer
from autobugfix.workspace import RepositoryWorkspace


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, shell=False)


def _repository(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "project"
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(root, "init")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Auto-Bug-Fix Tests")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "fixture")
    return root


def _evidence(*frames: tuple[str, int | None, str | None]) -> FailureEvidence:
    return FailureEvidence(
        source="traceback",
        raw_log="traceback",
        frames=tuple(
            StackFrame(SourceLocation(file=file, line=line), function=function)
            for file, line, function in frames
        ),
    )


def test_local_frames_rank_and_external_paths_are_not_read(tmp_path):
    root = _repository(tmp_path, {"src/service.py": "def process():\n    return 1 / 0\n"})
    result = PythonFaultLocalizer(RepositoryWorkspace.open(root)).localize(
        _evidence(("/usr/lib/python3.12/threading.py", 4, "run"), ("src/service.py", 2, "process"))
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].relative_path == "src/service.py"
    assert "traceback_exact_path" in result.candidates[0].evidence.sources
    assert "confirmed root cause" not in result.candidates[0].evidence.rank_reason


def test_absolute_suffix_and_symbol_metadata(tmp_path):
    root = _repository(
        tmp_path,
        {"src/service.py": "class Service:\n    @staticmethod\n    def process():\n        return 1\n"},
    )
    result = PythonFaultLocalizer(RepositoryWorkspace.open(root)).localize(
        _evidence((r"C:\runner\work\project\src\service.py", 4, "process"))
    )
    candidate = result.candidates[0]
    assert candidate.enclosing_class == "Service"
    assert candidate.enclosing_function == "process"
    assert candidate.line_start == 2  # decorator is part of the symbol span
    assert "traceback_absolute_suffix" in candidate.evidence.sources


def test_nested_async_function_is_narrowest(tmp_path):
    root = _repository(
        tmp_path,
        {"nested.py": "async def outer():\n    async def inner():\n        return 1\n    return await inner()\n"},
    )
    result = PythonFaultLocalizer(RepositoryWorkspace.open(root)).localize(
        _evidence(("nested.py", 3, "inner"))
    )
    assert result.candidates[0].enclosing_function == "outer.inner"


def test_ambiguous_basename_missing_file_and_syntax_diagnostic(tmp_path):
    root = _repository(
        tmp_path,
        {"a/utils.py": "def a():\n    pass\n", "b/utils.py": "def b():\n    pass\n", "broken.py": "def broken(:\n"},
    )
    result = PythonFaultLocalizer(RepositoryWorkspace.open(root)).localize(
        _evidence(("utils.py", 1, "a"), ("absent.py", 1, None), ("broken.py", 1, "broken"))
    )
    assert {candidate.relative_path for candidate in result.candidates} == {"broken.py"}
    assert any("unmatched traceback frame" in item for item in result.diagnostics if isinstance(item, str))
    assert any(getattr(item, "relative_path", None) == "broken.py" for item in result.diagnostics)
    assert result.candidates[0].ast_available is False


def test_traversal_traceback_path_is_not_used_for_mapping(tmp_path):
    root = _repository(tmp_path, {"outside.py": "value = 1\n", "inside.py": "value = 2\n"})
    result = PythonFaultLocalizer(RepositoryWorkspace.open(root)).localize(
        _evidence(("../../outside.py", 1, None))
    )
    assert result.candidates == ()
    assert any("unmatched traceback frame" in item for item in result.diagnostics if isinstance(item, str))


def test_limits_and_serialization_are_deterministic(tmp_path):
    root = _repository(tmp_path, {"a.py": "x = 1\n", "b.py": "x = 2\n"})
    evidence = _evidence(("a.py", 1, None), ("b.py", 1, None))
    localizer = PythonFaultLocalizer(RepositoryWorkspace.open(root), LocalizationLimits(max_candidates=1))
    first = localizer.localize(evidence).to_dict()
    second = localizer.localize(evidence).to_dict()
    assert first == second
    assert len(first["candidates"]) == 1
    assert first["truncated"] is True


def test_cli_path_uses_normalizer_and_workspace(tmp_path, capsys):
    root = _repository(tmp_path, {"main.py": "def run():\n    return 1\n"})
    from autobugfix.cli import main

    assert main(["localize", "--repo", str(root), "--log", 'Traceback (most recent call last):\n  File "main.py", line 2, in run\nValueError: bad', "--json"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["candidates"][0]["relative_path"] == "main.py"
