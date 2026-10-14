"""Command-line entry point."""

from __future__ import annotations

import typer
from rich.console import Console

from csuf_fullerton.__about__ import __version__
from csuf_fullerton.core.greeting import greet

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        # Plain print: machine-readable, no Rich number colouring under FORCE_COLOR.
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print the version and exit.",
    ),
) -> None:
    """csuf-fullerton command line."""


@app.command()
def hello(name: str = typer.Argument("world", help="Who to greet.")) -> None:
    """Print a greeting. Example command; replace with real ones."""
    try:
        console.print(greet(name))
    except ValueError as exc:
        console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


if __name__ == "__main__":
    app()
