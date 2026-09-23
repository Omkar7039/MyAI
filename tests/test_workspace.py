from pathlib import Path

import pytest

from tools.workspace import Workspace


def test_workspace_defaults_to_current_directory():
    workspace = Workspace()

    assert workspace.root == Path.cwd().resolve()


def test_workspace_resolves_relative_path(tmp_path: Path):
    workspace = Workspace(tmp_path)

    result = workspace.resolve("src")

    assert result == (tmp_path / "src").resolve()


def test_workspace_resolves_absolute_path_inside_root(
    tmp_path: Path,
):
    target = tmp_path / "example.txt"
    target.write_text(
        "hello",
        encoding="utf-8",
    )

    workspace = Workspace(tmp_path)

    assert workspace.resolve(target) == target.resolve()


def test_workspace_rejects_path_escape(tmp_path: Path):
    workspace = Workspace(tmp_path)

    with pytest.raises(
        ValueError,
        match="outside the allowed workspace",
    ):
        workspace.resolve("../outside.txt")


def test_workspace_file_and_directory_checks(
    tmp_path: Path,
):
    target = tmp_path / "example.txt"
    target.write_text(
        "hello",
        encoding="utf-8",
    )

    directory = tmp_path / "src"
    directory.mkdir()

    workspace = Workspace(tmp_path)

    assert workspace.exists("example.txt")
    assert workspace.is_file("example.txt")
    assert not workspace.is_directory("example.txt")

    assert workspace.exists("src")
    assert workspace.is_directory("src")
    assert not workspace.is_file("src")
