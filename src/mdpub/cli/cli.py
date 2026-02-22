"""CLI entrypoint: Typer app definition and command registration"""

import typer

from mdpub.cli.commands import build, commit, export, extract, init


app = typer.Typer(name="mdpub", no_args_is_help=True, help="Markdown document publishing pipeline")

app.command()(build)
app.command()(commit)
app.command()(export)
app.command()(extract)
app.command()(init)
