# Local parity with CI. `make check` is the whole PR gate.
.PHONY: install lint typecheck test build docker audit openspec check replicate replicate-full secrets nicaragua nicaragua-check brazil brazil-check

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

# Replication suite (change 0005). Fast runs in `make check`; full is manual or workflow_dispatch.
replicate:
	csuf-fullerton replicate --suite fast --out results/replication

replicate-full:
	csuf-fullerton replicate --suite full --out results/replication-full

# Secret scanning: git history, then the working tree including uncommitted data and results.
SCAN_DIRS = src tests data reports replication examples scripts docs openspec context-lake
secrets:
	gitleaks git --no-banner --redact --exit-code 1 .
	for d in $(SCAN_DIRS) $(wildcard results); do \
	  gitleaks dir --no-banner --redact --exit-code 1 $$d || exit 1; done

# Rebuild the reports from code and compare with the committed outputs.
nicaragua:
	bash scripts/reproduce_nicaragua.sh results/nicaragua

nicaragua-check: nicaragua
	python scripts/compare_outputs.py reports/nicaragua/outputs results/nicaragua

brazil:
	bash scripts/reproduce_brazil.sh results/brazil

brazil-check: brazil
	python scripts/compare_outputs.py reports/brazil/outputs results/brazil

check: lint typecheck test openspec harness replicate
