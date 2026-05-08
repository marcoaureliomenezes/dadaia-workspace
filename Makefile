.PHONY: install test lint typecheck format clean

install:
	poetry install

test:
	poetry run pytest tests/ -v --tb=short

lint:
	poetry run ruff check dadaia_workspace/ tests/

typecheck:
	poetry run mypy dadaia_workspace/

format:
	poetry run ruff format dadaia_workspace/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache dist
