import tomllib
from pathlib import Path

project = "System Prompt Builder"
author = "Ivan Willig"

_project_root = Path(__file__).resolve().parents[1]
with (_project_root / "pyproject.toml").open("rb") as pyproject_file:
    _metadata = tomllib.load(pyproject_file)["project"]

release = str(_metadata["version"])
version = release

extensions: list[str] = []
templates_path = ["_templates"]
exclude_patterns = ["_build"]
html_theme = "furo"
