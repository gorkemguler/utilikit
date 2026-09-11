"""``utilikit`` command-line entry point."""

from __future__ import annotations

import secrets

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import get_settings

app = typer.Typer(add_completion=False, help="Utilikit - a self-hostable HTTP toolbox API.")
console = Console()


@app.command()
def version() -> None:
    console.print(f"utilikit {__version__}")


@app.command("gen-key")
def gen_key() -> None:
    """Print a random API key for UTILIKIT_API_KEYS."""
    console.print(secrets.token_urlsafe(32))


@app.command()
def config() -> None:
    """Show the effective configuration (secrets masked)."""
    s = get_settings()
    t = Table(title="Utilikit configuration", show_header=False)
    for k, v in s.model_dump().items():
        shown = "****" if k == "api_keys" and v else str(v)
        t.add_row(k, shown)
    console.print(t)


@app.command()
def tools() -> None:
    """List every registered tool and its endpoints."""
    import utilikit.tools  # noqa: F401  (populate registry)

    from .registry import catalog

    for info in catalog():
        console.print(f"[bold]{info.title}[/bold]  [dim]({info.category})[/dim]")
        for e in info.endpoints:
            console.print(f"  {e.method:5} {e.path}")


@app.command()
def serve(host: str = typer.Option(None), port: int = typer.Option(None), reload: bool = typer.Option(False)) -> None:
    """Run the API server."""
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "utilikit.app:app",
        host=host or s.host,
        port=port or s.port,
        reload=reload,
        log_level=s.log_level.lower(),
    )


@app.command()
def selftest() -> None:
    """Import everything and report how many tools registered."""
    from .app import create_app

    create_app()
    from .registry import catalog

    console.print(f"[green]OK[/green] {len(catalog())} tools registered")
    for c in sorted({t.category for t in catalog()}):
        console.print(f"  • {c}")


if __name__ == "__main__":
    app()
