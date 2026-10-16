
import pytest

def test_inner(request: pytest.FixtureRequest):
    (request.config.rootpath / ".ruff_cache").mkdir(exist_ok=True)
