"""CLI entrypoint: Typer app definition and command registration"""

import typer

from mdpub.cli.commands import build_cmd, list_cmd, commit_cmd, export_cmd, extract_cmd, init_cmd


app = typer.Typer(name="mdpub", no_args_is_help=True, help="Markdown document publishing pipeline")

app.command(name="build")(build_cmd)
app.command(name="list")(list_cmd)
app.command(name="commit")(commit_cmd)
app.command(name="export")(export_cmd)
app.command(name="extract")(extract_cmd)
app.command(name="init")(init_cmd)
