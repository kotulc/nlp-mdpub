"""Integration test for the build command (extract -> commit -> export pipeline)"""

from typer.testing import CliRunner

from mdpub.cli.cli import app


def test_build_cmd_runs_full_pipeline(tmp_path, monkeypatch):
    """build produces .mdx and .json output files for each extracted document."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "hello.md").write_text("# Hello\n\nWorld\n")

    runner = CliRunner()
    result = runner.invoke(app, [
        "build", "hello.md",
        "--db-url", f"sqlite:///{tmp_path}/test.db",
        "--out-dir", str(tmp_path / "dist"),
    ])

    assert result.exit_code == 0, result.output
    assert any((tmp_path / "dist").rglob("*.mdx"))
    assert any((tmp_path / "dist").rglob("*.json"))
