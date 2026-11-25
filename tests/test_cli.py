import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from findex.cli import app
from findex.index import Index
from findex.store import save

runner = CliRunner()


@pytest.fixture
def index_file(tiny_index: Index, tmp_path: Path) -> Path:
    path = tmp_path / "index.bin"
    save(tiny_index, path)
    return path


def test_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "index" in result.output
    assert "search" in result.output
    assert "stats" in result.output


def test_index(tiny_corpus: Path, tmp_path: Path) -> None:
    path = tmp_path / "index.bin"

    result = runner.invoke(
        app,
        ["index", str(tiny_corpus), "--out", str(path)],
    )

    assert result.exit_code == 0
    assert path.exists()
    assert "Documents: 5" in result.output


def test_search_table(index_file: Path) -> None:
    result = runner.invoke(
        app,
        ["search", "python", "--index", str(index_file)],
    )

    assert result.exit_code == 0
    assert "Search results" in result.output
    assert "doc4" in result.output


@pytest.mark.parametrize("scorer", ["bm25", "tfidf"])
def test_search_json(index_file: Path, scorer: str) -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "python",
            "--index",
            str(index_file),
            "--scorer",
            scorer,
            "--k",
            "2",
            "--json",
        ],
    )

    assert result.exit_code == 0

    data = json.loads(result.stdout)

    assert len(data) == 2
    assert data[0]["doc_id"] == 4
    assert "score" in data[0]
    assert "title" in data[0]


def test_stats(index_file: Path) -> None:
    result = runner.invoke(
        app,
        ["stats", "--index", str(index_file)],
    )

    assert result.exit_code == 0
    assert "Documents" in result.output
    assert "Terms" in result.output


def test_missing_index(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "python",
            "--index",
            str(tmp_path / "missing.bin"),
        ],
    )

    assert result.exit_code != 0
    assert "Error:" in result.stderr
    assert "Traceback" not in result.output


def test_missing_directory(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["index", str(tmp_path / "missing")],
    )

    assert result.exit_code != 0
    assert "Error:" in result.stderr
    assert "Traceback" not in result.output


def test_invalid_query(index_file: Path) -> None:
    result = runner.invoke(
        app,
        ["search", "python AND", "--index", str(index_file)],
    )

    assert result.exit_code != 0
    assert "Error:" in result.stderr


@pytest.mark.parametrize("verbosity", ["-v", "-vv"])
def test_logging(index_file: Path, verbosity: str) -> None:
    result = runner.invoke(
        app,
        [
            verbosity,
            "search",
            "python",
            "--index",
            str(index_file),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert "[TIMED]" in result.stderr
    assert "[TIMED]" not in result.stdout
    assert isinstance(json.loads(result.stdout), list)


def test_no_results(index_file: Path) -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "unknownword",
            "--index",
            str(index_file),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout) == []
