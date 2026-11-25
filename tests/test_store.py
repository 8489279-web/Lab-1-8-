from pathlib import Path

import pytest

from findex.index import Index, build_index
from findex.store import load, open_index, save


@pytest.mark.parametrize("extension", [".bin", ".json"])
def test_save(
    tiny_index: Index,
    tmp_path: Path,
    extension: str,
) -> None:
    path = tmp_path / ("index" + extension)

    save(tiny_index, path)

    assert path.exists()
    assert path.stat().st_size > 0


@pytest.mark.parametrize("extension", [".bin", ".json"])
def test_save_load_equality(
    tiny_index: Index,
    tmp_path: Path,
    extension: str,
) -> None:
    path = tmp_path / ("index" + extension)

    save(tiny_index, path)
    restored = load(path)

    assert restored == tiny_index


@pytest.mark.parametrize("extension", [".bin", ".json"])
def test_preserve_positions(
    tiny_index: Index,
    tmp_path: Path,
    extension: str,
) -> None:
    path = tmp_path / ("index" + extension)

    save(tiny_index, path)
    restored = load(path)

    assert restored["python"][-1].positions == (0, 1)


@pytest.mark.parametrize("extension", [".bin", ".json"])
def test_open_index(
    tiny_index: Index,
    tmp_path: Path,
    extension: str,
) -> None:
    path = tmp_path / ("index" + extension)

    save(tiny_index, path)

    with open_index(path) as restored:
        assert restored == tiny_index


@pytest.mark.parametrize("extension", [".bin", ".json"])
def test_empty_index(
    tmp_path: Path,
    extension: str,
) -> None:
    index = build_index(tmp_path)
    path = tmp_path / ("empty" + extension)

    save(index, path)

    assert load(path) == index


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "missing.bin")


def test_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("invalid json", encoding="utf-8")

    with pytest.raises(ValueError):
        load(path)
