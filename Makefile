SHELL := /bin/sh
COMPOSE := docker compose --env-file .env

.PHONY: bootstrap demo-data bundle-ready up down demo-up logs ps ingest dbt-build query test lint validate terraform-fmt terraform-validate

bootstrap:
	@test -f .env || cp .env.example .env

demo-data:
	@docker run --rm \
		-v "$(CURDIR)/data:/opt/data-platform/data" \
		portable-data-platform:local \
		python scripts/generate_demo_data.py

bundle-ready: bootstrap
	$(COMPOSE) build platform-code
	$(MAKE) demo-data

up: bootstrap
	$(COMPOSE) build
	$(MAKE) demo-data
	$(COMPOSE) --profile local up -d

demo-up: bootstrap
	$(COMPOSE) build
	$(MAKE) demo-data
	$(COMPOSE) --profile local --profile demo up -d

down:
	$(COMPOSE) --profile local --profile demo down

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) --profile local --profile demo ps

ingest:
	$(COMPOSE) exec dagster-daemon dagster asset materialize --select 'group:ingestion' -m data_platform.definitions

dbt-build:
	$(COMPOSE) exec dagster-daemon dbt build --project-dir /opt/data-platform/dbt --profiles-dir /opt/data-platform/dbt

query:
	$(COMPOSE) run --rm platform-code python -m data_platform.duckdb_cli /opt/data-platform/data/inbox/customers.csv

test:
	$(COMPOSE) run --rm --no-deps platform-code pytest -q

lint:
	python3 -m ruff check src tests scripts

terraform-fmt:
	terraform -chdir=terraform fmt -recursive -check

terraform-validate:
	terraform -chdir=terraform validate

validate:
	$(COMPOSE) --profile local --profile demo config --quiet
	python3 -m compileall -q src tests scripts
	terraform -chdir=terraform fmt -recursive -check
