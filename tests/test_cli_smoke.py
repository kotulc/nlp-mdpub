from typer.testing import CliRunner
from mdpub.cli import app

def test_cli_smoke():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
