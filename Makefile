# Local parity with CI. `make check` is the whole PR gate.
.PHONY: install lint typecheck test build docker audit openspec check

install:
	python3.12 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]" build twine && .venv/bin/pre-commit install

lint:
	ruff check . && ruff format --check .

typecheck:
	mypy

test:
	pytest -m "not network" --cov --cov-report=term-missing --cov-fail-under=85

build:
	python -m build && twine check --strict dist/*

docker:
	docker build -t espin086/csuf-fullerton:local . && docker run --rm espin086/csuf-fullerton:local --version

audit:
	pip freeze --exclude-editable > requirements-audit.txt && pip-audit --strict -r requirements-audit.txt

openspec:
	openspec validate --all

harness:
	bash scripts/check-agent-links.sh

check: lint typecheck test openspec harness
