.PHONY: setup install test test-visual test-smoke update-snapshots up down clean

PYTHON ?= python3

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

## Download UIX into custom_components/ (latest release)
setup:
	$(PYTHON) scripts/fetch_uix.py

## Download a specific UIX version: make setup-version VERSION=5.3.1
setup-version:
	$(PYTHON) scripts/fetch_uix.py $(VERSION)

## Install Python dependencies (test extras)
install:
	pip install -e ".[test]"
	playwright install chromium

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

## Run all unit/integration tests (no browser)
test:
	pytest tests/ -v --ignore=tests/visual

## Run visual (Playwright) tests — requires setup + install
test-visual:
	pytest tests/visual/ -v

## Run version smoke tests (pulls stable, beta, dev images — slow)
test-smoke:
	pytest tests/test_container.py -v -m version_smoke

## Refresh all visual baselines (overwrite existing PNGs)
update-snapshots:
	SNAPSHOT_UPDATE=1 pytest tests/visual/ -v

# ---------------------------------------------------------------------------
# Local dev server
# ---------------------------------------------------------------------------

## Start HA locally with docker compose
up:
	docker compose up

## Stop local HA
down:
	docker compose down

# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------

## Remove downloaded UIX, pytest cache, and snapshot actuals
clean:
	rm -rf custom_components/uix
	rm -rf .pytest_cache __pycache__ tests/__pycache__ tests/visual/__pycache__
	find tests/visual/snapshots -name "*.actual.png" -delete
