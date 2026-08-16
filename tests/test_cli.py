from autobugfix.cli import main


def test_cli_help(capsys):
    assert main([]) == 0
    assert "mvp-fix" in capsys.readouterr().out

