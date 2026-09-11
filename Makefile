.DEFAULT_GOAL := help
PY ?= python

.PHONY: help install dev browser lint fmt test run docker clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Install (core only)
	$(PY) -m pip install -e .

dev: ## Install with dev + all optional extras
	$(PY) -m pip install -e ".[dev,browser,decode,geo]"

browser: ## Download the Chromium Playwright build
	playwright install --with-deps chromium

lint: ## ruff check + format check
	ruff check .
	ruff format --check .

fmt: ## Auto-format
	ruff check --fix .
	ruff format .

test: ## Run the test suite
	pytest

run: ## Run the dev server (auto-reload)
	utilikit serve --reload

docker: ## Build the container image
	docker build -t utilikit:local .

clean: ## Remove caches / build artefacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info var
	find . -name __pycache__ -type d -exec rm -rf {} +
