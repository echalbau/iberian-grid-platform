.DEFAULT_GOAL := help
SHELL := /bin/bash

PYTHON ?= python3.11
VENV := .venv
ANALYTICS_VENV := .venv-analytics
BIN := $(VENV)/bin
ANALYTICS_BIN := $(ANALYTICS_VENV)/bin

PIP_VERSION := 26.2.1
AIRFLOW_VERSION := 3.3.2
AIRFLOW_CONSTRAINTS := https://raw.githubusercontent.com/apache/airflow/constraints-$(AIRFLOW_VERSION)/constraints-3.11.txt
TERRAFORM_IMAGE := hashicorp/terraform:1.16.5

COMPOSE := docker compose --env-file .env -f docker/docker-compose.yml
DBT := cd dbt && DBT_PROFILES_DIR=. ../$(ANALYTICS_BIN)/dbt

# Day to process, e.g. `make ingest-ree-demand DATE=2025-04-28`.
DATE ?=

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-22s %s\n", $$1, $$2}'

# --- Environments ------------------------------------------------------------

.PHONY: setup
setup: $(VENV)/.installed $(ANALYTICS_VENV)/.installed ## Create both virtualenvs and install git hooks
	@if [ -d .git ]; then $(BIN)/pre-commit install; fi

# Airflow is installed first with its official constraints file; the project
# pins are chosen to agree with it (see docs/decisions/0003).
$(VENV)/.installed: pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --quiet pip==$(PIP_VERSION)
	$(BIN)/pip install --quiet "apache-airflow==$(AIRFLOW_VERSION)" --constraint $(AIRFLOW_CONSTRAINTS)
	$(BIN)/pip install --quiet -e ".[dev,spark]"
	@touch $@

# dbt and the dashboard live in their own virtualenv so their dependency tree
# never has to be reconciled with Airflow's.
$(ANALYTICS_VENV)/.installed: requirements/analytics.txt
	$(PYTHON) -m venv $(ANALYTICS_VENV)
	$(ANALYTICS_BIN)/pip install --quiet pip==$(PIP_VERSION)
	$(ANALYTICS_BIN)/pip install --quiet -r requirements/analytics.txt
	@touch $@

.env:
	cp .env.example .env
	@echo "Created .env from .env.example - review it before going beyond local use."

# --- Quality -----------------------------------------------------------------

.PHONY: lint
lint: $(VENV)/.installed ## Run ruff (lint + format check) and sqlfluff
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	$(BIN)/sqlfluff lint dbt/models

.PHONY: format
format: $(VENV)/.installed ## Auto-format Python code
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

.PHONY: test
test: $(VENV)/.installed ## Run unit tests (no Docker needed; Spark tests need Java)
	$(BIN)/pytest -m "not integration"

.PHONY: test-integration
test-integration: $(VENV)/.installed .env ## Run integration tests against the running stack
	set -a && source .env && set +a && $(BIN)/pytest -m integration

# --- Local stack -------------------------------------------------------------

.PHONY: up
up: .env ## Build and start Airflow, Spark and MinIO
	$(COMPOSE) up --detach --build --wait
	@echo "Airflow  http://localhost:8080"
	@echo "MinIO    http://localhost:9001"
	@echo "Spark    http://localhost:8081"

.PHONY: down
down: ## Stop the stack (keeps volumes)
	$(COMPOSE) down

.PHONY: destroy
destroy: ## Stop the stack and delete its volumes
	$(COMPOSE) down --volumes

.PHONY: ps
ps: ## Show stack status
	$(COMPOSE) ps

.PHONY: logs
logs: ## Tail stack logs
	$(COMPOSE) logs --follow --tail 100

# --- Pipelines ---------------------------------------------------------------

.PHONY: ingest-ree-demand
ingest-ree-demand: $(VENV)/.installed .env ## Ingest one day of REE demand to bronze from the host (DATE=YYYY-MM-DD)
	@test -n "$(DATE)" || (echo "Usage: make $@ DATE=YYYY-MM-DD" && exit 1)
	set -a && source .env && set +a && $(BIN)/grid-platform ingest ree-demand --date $(DATE)

.PHONY: trigger-ree-demand
trigger-ree-demand: ## Trigger the ingest_ree_demand DAG in Airflow (DATE=YYYY-MM-DD)
	@test -n "$(DATE)" || (echo "Usage: make $@ DATE=YYYY-MM-DD" && exit 1)
	$(COMPOSE) exec airflow-scheduler airflow dags unpause ingest_ree_demand
	$(COMPOSE) exec airflow-scheduler airflow dags trigger ingest_ree_demand --conf '{"target_date": "$(DATE)"}'

.PHONY: silver
silver: ## Run bronze_to_silver on the Spark cluster (DATE=YYYY-MM-DD)
	@test -n "$(DATE)" || (echo "Usage: make $@ DATE=YYYY-MM-DD" && exit 1)
	$(COMPOSE) exec spark-master /opt/spark/bin/spark-submit \
		--master spark://spark-master:7077 \
		/opt/project/src/grid_platform/spark_jobs/bronze_to_silver.py \
		--dataset ree_demand --date $(DATE)

.PHONY: dbt-build
dbt-build: $(ANALYTICS_VENV)/.installed .env ## Run and test dbt models with the local DuckDB profile
	set -a && source .env && set +a && $(DBT) build --target dev

.PHONY: dbt-parse
dbt-parse: $(ANALYTICS_VENV)/.installed ## Parse the dbt project (no data access)
	$(DBT) parse --target dev

.PHONY: dashboard
dashboard: $(ANALYTICS_VENV)/.installed .env ## Run the Streamlit dashboard
	set -a && source .env && set +a && $(ANALYTICS_BIN)/streamlit run dashboard/Home.py

# --- Infrastructure ----------------------------------------------------------

.PHONY: tf-validate
tf-validate: ## terraform fmt -check and validate, in Docker (never applies)
	docker run --rm -v "$(CURDIR)/infra/terraform:/workspace" -w /workspace $(TERRAFORM_IMAGE) fmt -check -recursive
	docker run --rm -v "$(CURDIR)/infra/terraform:/workspace" -w /workspace $(TERRAFORM_IMAGE) init -backend=false -input=false
	docker run --rm -v "$(CURDIR)/infra/terraform:/workspace" -w /workspace $(TERRAFORM_IMAGE) validate

# --- Housekeeping ------------------------------------------------------------

.PHONY: clean
clean: ## Remove caches and build artifacts (keeps virtualenvs and .env)
	rm -rf .pytest_cache .ruff_cache build dist dbt/target dbt/logs spark-warehouse
	find . -name __pycache__ -type d -not -path "./.venv*" -prune -exec rm -rf {} +
