# Common local checks and throwaway development instances.
.DEFAULT_GOAL := help

# Home Assistant version both development instances run. Exported, so
# compose.yaml resolves its image tag from the same value; override with
# HA_VERSION=...
export HA_VERSION ?= 2026.11.0
# Firmware config validated by `esphome-config` and compiled by
# `esphome-compile`; override with CONFIG=...
CONFIG ?= esphome/nspanel_haui_universal.yaml
# Optional arguments for targets that take them, e.g. ARGS=--draft
ARGS ?=

.PHONY: help check test test-integration test-frontend format format-check lint typecheck typecheck-frontend docs hmi-check screens-check image-preview version-check generated-check esphome-config esphome-compile esphome-size \
	ha-venv-setup ha-venv-start ha-venv-logs \
	ha-docker-up ha-docker-stop ha-docker-restart ha-docker-logs ha-docker-down

help: ## Show available targets
	@awk 'BEGIN { FS = ":.*##"; print "Targets:" } /^[a-zA-Z0-9_-]+:.*##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

check: test format-check lint typecheck typecheck-frontend docs version-check generated-check ## Run routine local validation (excludes ESPHome config)

test: test-integration test-frontend ## Run all tests (integration + frontend)

test-integration: ## Run backend tests (Python dev environment + Node 22+)
	pytest tests/

test-frontend: ## Run frontend tests (Node 22+)
	node --test 'tests/frontend/*.test.mjs'

format: ## Format Python code with ruff
	ruff format custom_components/ scripts/ tests/

format-check: ## Check Python formatting with ruff
	ruff format --check custom_components/ scripts/ tests/

lint: ## Lint Python code with ruff
	ruff check custom_components/ scripts/

typecheck: ## Type-check the integration package
	mypy

typecheck-frontend: ## Type-check editor modules marked with @ts-check (npm ci first)
	npm run typecheck:frontend

docs: ## Build documentation strictly (requirements-docs.txt)
	zensical build --strict

version-check: ## Check the integration version and its firmware mirrors
	python -m scripts.bump_version --check

generated-check: ## Check that the icon cheatsheet and translations are current
	python -m scripts.font_tools.gen_cheatsheet --check
	python -m scripts.translations.extract_translations --check

# The HMI specs are the source, so this only runs the tests that guard them;
# keep it that way instead of listing the generators again.
hmi-check: ## Verify HMI layouts, generated layout assets, and preview coverage
	pytest -q tests/test_gen_layout.py tests/test_virtual_layout.py tests/test_preview_coverage.py

screens-check: ## Compare docs/screens.html and its PNGs with a fresh render (Chrome + Node 22+)
	python -m scripts.preview_gallery.gen_preview_gallery --check

image-preview: ## Render what show_image draws for a file (ARGS="logo.png --x 20")
	python -m scripts.image_program.gen_image_preview $(ARGS)

esphome-config: ## Validate universal ESPHome config (separate ESPHome environment)
	esphome config $(CONFIG)

esphome-compile: ## Compile a firmware config (CONFIG=..., separate ESPHome environment)
	esphome compile $(CONFIG)

esphome-size: ## Check the newest firmware image against its app partition
	python -m scripts.verify_firmware.check_size

# python3.14 explicitly: without an active .venv, `python` may be an older release.
ha-venv-setup: ## Create the Home Assistant venv and link this integration
	python3.14 -m venv .venv_ha
	.venv_ha/bin/python -m pip install homeassistant==$(HA_VERSION)
	mkdir -p .dev/ha-config/custom_components
	ln -sfn "$(CURDIR)/custom_components/nspanel_haui" .dev/ha-config/custom_components/nspanel_haui

ha-venv-start: ## Start the virtualenv Home Assistant instance (Ctrl+C to stop)
	.venv_ha/bin/hass -c .dev/ha-config

ha-venv-logs: ## Follow virtualenv Home Assistant logs
	tail -f .dev/ha-config/home-assistant.log

ha-docker-up: ## Start the Docker Home Assistant instance
	docker compose up -d

ha-docker-stop: ## Stop Docker Home Assistant, preserving its config
	docker compose stop

ha-docker-restart: ## Restart Docker Home Assistant
	docker compose restart

ha-docker-logs: ## Follow Docker Home Assistant logs
	docker compose logs -f

ha-docker-down: ## Remove Docker container, preserving its config
	docker compose down
