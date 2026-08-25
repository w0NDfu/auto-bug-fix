import json

import pytest

import autobugfix
from autobugfix.cli import main
from backend.llm.factory import get_llm
from backend.llm.mock import MockLLM


def test_cli_help(capsys):
    assert main([]) == 0
    output = capsys.readouterr().out
    assert "mvp-fix" in output
    assert "codex-handoff" in output


def test_package_version():
    assert autobugfix.__version__ == "0.1.0.dev0"


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == autobugfix.__version__


def test_mock_provider_is_selected_without_credentials(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    assert isinstance(get_llm(), MockLLM)


def test_mvp_cli_is_deterministic_and_offline(capsys, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    assert main(["mvp-fix", "--log", "ZeroDivisionError: division by zero"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "fixed"
    assert result["iterations"] == 1


@pytest.mark.parametrize("argv", [["unknown"], ["mvp-fix"]])
def test_malformed_cli_usage_exits_with_usage_error(argv):
    with pytest.raises(SystemExit) as exc_info:
        main(argv)
    assert exc_info.value.code == 2
