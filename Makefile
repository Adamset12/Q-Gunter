.PHONY: help test lint format typecheck check ci clean run run-raw

help:
	@echo "Q-Gunter Commands"
	@echo "================="
	@echo "  make test       Run all tests"
	@echo "  make test-cov   Run tests with coverage"
	@echo "  make lint       Run linter"
	@echo "  make format     Format code"
	@echo "  make typecheck  Run type checker"
	@echo "  make check      Run lint + typecheck"
	@echo "  make ci         Full CI simulation"
	@echo "  make clean      Clean build artifacts"
	@echo "  make run        Run Q-Gunter (example)"
	@echo "  make run-raw    Run in raw mode (example)"

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=qgunter --cov-report=term-missing

lint:
	uv run ruff check qgunter/ tests/

lint-fix:
	uv run ruff check --fix qgunter/ tests/

format:
	uv run ruff format qgunter/ tests/

format-check:
	uv run ruff format --check qgunter/ tests/

typecheck:
	uv run mypy qgunter/

check: lint typecheck

ci:
	@echo "=== CI Simulation ==="
	uv run ruff check qgunter/ tests/
	uv run ruff format --check qgunter/ tests/
	uv run mypy qgunter/
	uv run pytest tests/ -v
	uv build
	@echo "=== CI Passed ==="

build:
	uv build

clean:
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

run:
	uv run q-gunter --target example.com

run-raw:
	uv run q-gunter --target example.com --raw