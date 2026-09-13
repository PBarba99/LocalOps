"""Keep source and packaging versions aligned for releases."""

from pathlib import Path
import tomllib

from localops import __version__


def test_package_version_matches_project_metadata() -> None:
    project_file = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with project_file.open("rb") as source:
        metadata = tomllib.load(source)

    assert __version__ == metadata["project"]["version"]
