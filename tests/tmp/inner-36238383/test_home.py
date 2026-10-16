
import os, subprocess, sys
from pathlib import Path
from tests.fixtures.harness_env import suite_env

def test_inner():
    assert "DADAIA_CONTEXT" not in os.environ
    assert Path.home() != Path(os.environ["OUTER_FOREIGN_HOME"])
    child = subprocess.run(
        [sys.executable, "-c", "import os; print(os.environ['HOME'])"],
        env=suite_env(os.environ, Path.home()), capture_output=True, text=True, check=True,
    )
    assert child.stdout == f"{Path.home()}\n"
