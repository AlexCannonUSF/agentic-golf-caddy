"""IDE-friendly launcher: click Run to start Streamlit app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"


def _reexec_with_project_venv_if_needed() -> None:
    """
    If launched with the wrong interpreter in IntelliJ/PyCharm, re-launch
    with the repo's .venv interpreter automatically.
    """

    if not PROJECT_VENV_PYTHON.exists():
        return

    current_python = Path(sys.executable).resolve()
    preferred_python = PROJECT_VENV_PYTHON.resolve()

    if current_python == preferred_python:
        return

    os.execv(
        str(preferred_python),
        [str(preferred_python), str(Path(__file__).resolve()), *sys.argv[1:]],
    )


def main() -> int:
    _reexec_with_project_venv_if_needed()

    try:
        from streamlit.web import cli as stcli
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Streamlit is not installed for the active interpreter. "
            "Create/install the project venv and run again."
        ) from exc

    app_path = PROJECT_ROOT / "app.py"
    sys.argv = ["streamlit", "run", str(app_path)]
    return stcli.main()


if __name__ == "__main__":
    raise SystemExit(main())
