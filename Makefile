# Common local checks and throwaway development instances.
.DEFAULT_GOAL := help

.PHONY: help check test test-frontend format lint typecheck typecheck-frontend docs hmi-check esphome-config \
	ha-venv-setup ha-venv-start ha-venv-logs \
	ha-docker-up ha-docker-stop ha-docker-restart ha-docker-logs ha-docker-down

help: ## Show available targets
	@awk 'BEGIN { FS = ":.*##"; print "Targets:" } /^[a-zA-Z0-9_-]+:.*##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

check: test test-frontend lint typecheck typecheck-frontend docs hmi-check ## Run routine local validation (excludes ESPHome config)

test: ## Run backend tests (Python dev environment + Node 22+)
	pytest tests/

test-frontend: ## Run frontend tests (Node 22+)
	node --test 'tests/frontend/*.test.mjs'

format: ## Format Python code with ruff
	ruff format custom_components/ scripts/

lint: ## Lint Python code with ruff
	ruff check custom_components/ scripts/

typecheck: ## Type-check the haui core
	mypy

typecheck-frontend: ## Type-check editor modules marked with @ts-check (npm ci first)
	npm run typecheck:frontend

docs: ## Build documentation strictly (requirements-docs.txt)
	zensical build --strict

hmi-check: ## Verify HMI layouts, generated layout assets, and preview coverage
	python -m scripts.hmi_layout.gen_layout --check
	python -m scripts.hmi_layout.gen_layout --spec portrait --check
	python -m scripts.verify_nextion.verify_nextion --require-portrait
	python -m scripts.hmi_layout.gen_virtual_layout --check
	python -m scripts.check_preview_coverage

esphome-config: ## Validate universal ESPHome config (separate ESPHome environment)
	esphome config esphome/nspanel_haui_universal.yaml

ha-venv-setup: ## Create the HA 2026.11 venv and link this integration
	python3.14 -m venv .venv_ha
	.venv_ha/bin/pip install homeassistant==2026.11.0
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
