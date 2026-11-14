"""Checks for this repository's own prompt and evaluation suite."""

import subprocess
import sys
from pathlib import Path

from spb.evaluation import load_evaluation_suite

ROOT = Path(__file__).resolve().parents[1]


def test_python_testing_fragment_example_runs_under_pytest(tmp_path: Path) -> None:
    fragment = (ROOT / ".spb/fragments/python_testing/FRAGMENT.md").read_text(
        encoding="utf-8"
    )
    example = fragment.split("```python\n", 1)[1].split("\n```", 1)[0]
    test_file = tmp_path / "test_hegel_example.py"
    test_file.write_text(example + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(test_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_evaluation_suite_covers_regressions() -> None:
    suite = load_evaluation_suite(ROOT / ".spb/evals/project-assistant.yaml")
    cases = {case.name: case for case in suite.cases}
    assert "Write an executable Hegel test" in cases
    assert "Avoid unsupported certainty about static analysis" in cases
    assert (
        "at most two sentences"
        in cases["Avoid unsupported certainty about static analysis"].input
    )
