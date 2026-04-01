.PHONY: setup fetch-plugin list-releases list-plugin-releases install test test-visual test-smoke update-snapshots up down clean

PYTHON ?= python3

# The default component to fetch when running `make setup`.
# Override on the command line: make setup COMPONENT=custom-cards/button-card
COMPONENT ?= Lint-Free-Technology/uix

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

## Fetch the latest release of COMPONENT into custom_components/
## Usage:  make setup
##         make setup COMPONENT=owner/repo
##         make setup COMPONENT=owner/repo VERSION=5.3.1
setup:
	$(PYTHON) scripts/fetch_component.py $(COMPONENT) $(VERSION)

## List releases for COMPONENT
## Usage:  make list-releases COMPONENT=owner/repo
list-releases:
	$(PYTHON) scripts/fetch_component.py $(COMPONENT) --list

## Download a frontend dashboard plugin (JS) and register it as a Lovelace resource
## Usage:  make fetch-plugin PLUGIN=owner/repo
##         make fetch-plugin PLUGIN=owner/repo VERSION=1.2.3
fetch-plugin:
	$(PYTHON) scripts/fetch_plugin.py $(PLUGIN) $(VERSION)

## List available releases for a dashboard plugin
## Usage:  make list-plugin-releases PLUGIN=owner/repo
list-plugin-releases:
	$(PYTHON) scripts/fetch_plugin.py $(PLUGIN) --list

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

## Remove all downloaded custom components, plugins, pytest cache, and snapshot actuals
clean:
	find custom_components -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
	find ha-config/www/dashboard -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache __pycache__ tests/__pycache__ tests/visual/__pycache__
	find tests/visual/snapshots -name "*.actual.png" -delete
