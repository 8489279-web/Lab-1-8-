import json
import logging
import pickle
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from findex.index import ExecutorName, build_index
from findex.ranking import search as ranked_search
from findex.scoring import ScorerName, get_scorer
from findex.store import load, save

app = typer.Typer(no_args_is_help=True)

console = Console()
error_console = Console(stderr=True)


def fail(message: str) -> None:
    error_console.print(f"Error: {message}", markup=False)
    raise typer.Exit(code=1)


@app.callback()
def main(
    verbose: Annotated[
        int,
        typer.Option("--verbose", "-v", count=True),
    ] = 0,
) -> None:
    level = logging.WARNING

    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        force=True,
    )


@app.command("index")
def index_command(
    directory: Path,
    out: Annotated[
        Path,
        typer.Option("--out", "-o"),
    ] = Path("index.bin"),
    workers: Annotated[
        int,
        typer.Option("--workers", min=1),
    ] = 1,
    executor: Annotated[
        ExecutorName,
        typer.Option("--executor"),
    ] = "serial",
) -> None:
    if not directory.is_dir():
        fail(f"Directory not found: {directory}")

    try:
        with Progress(console=console) as progress:
            task = progress.add_task(
                "Building index...",
                total=None,
            )

            index = build_index(
                directory,
                with_positions=True,
                workers=workers,
                executor=executor,
            )

            save(index, out)

            progress.update(task, total=1, completed=1)

        console.print(f"Executor: {executor}")
        console.print(f"Requested workers: {workers}")
        console.print(f"Documents: {index.num_docs}")
        console.print(f"Terms: {len(index)}")
        console.print(f"Index saved: {out}")

    except (OSError, ValueError) as error:
        fail(str(error))


@app.command("search")
def search_command(
    query: str,
    index_path: Annotated[
        Path,
        typer.Option("--index", "-i"),
    ] = Path("index.bin"),
    scorer: Annotated[
        ScorerName,
        typer.Option("--scorer"),
    ] = "bm25",
    k: Annotated[
        int,
        typer.Option("--k", min=1),
    ] = 10,
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    try:
        index = load(index_path)

        results = ranked_search(
            index,
            query,
            get_scorer(scorer),
            k,
        )

        if json_output:
            data = [
                {
                    "doc_id": result.doc_id,
                    "title": result.title,
                    "score": result.score,
                }
                for result in results
            ]

            typer.echo(json.dumps(data, ensure_ascii=False))
            return

        table = Table(title="Search results")

        table.add_column("Rank")
        table.add_column("Document ID")
        table.add_column("Title")
        table.add_column("Score")

        for rank, result in enumerate(results, 1):
            table.add_row(
                str(rank),
                str(result.doc_id),
                result.title,
                f"{result.score:.6f}",
            )

        console.print(table)
        console.print(f"Results: {len(results)}")

    except (OSError, ValueError, TypeError, EOFError, pickle.UnpicklingError) as error:
        fail(str(error))


@app.command("stats")
def stats_command(
    index_path: Annotated[
        Path,
        typer.Option("--index", "-i"),
    ] = Path("index.bin"),
) -> None:
    try:
        index = load(index_path)

        table = Table(title="Index statistics")
        table.add_column("Parameter")
        table.add_column("Value")

        table.add_row("Documents", str(index.num_docs))
        table.add_row("Terms", str(len(index)))
        table.add_row(
            "Average document length",
            f"{index.avg_doc_length:.2f}",
        )
        table.add_row(
            "File size",
            f"{index_path.stat().st_size} bytes",
        )

        console.print(table)

    except (OSError, ValueError, TypeError, EOFError, pickle.UnpicklingError) as error:
        fail(str(error))


if __name__ == "__main__":
    app()
