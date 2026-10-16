
from pathlib import Path

def test_inner():
    (Path(__file__).parent / "__pycache__").mkdir()
