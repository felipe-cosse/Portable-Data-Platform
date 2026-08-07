SHELL := /bin/sh
COMPOSE := docker compose --env-file .env

.PHONY: bootstrap demo-data bundle-ready up down demo-up bi-up metabase-provision logs bi-logs ps ingest dbt-build query test lint validate smoke bi-smoke terraform-fmt terraform-validate

bootstrap:
	@test -f .env || cp .env.example .env
	@if ! awk -F= '$$1 == "METABASE_ENCRYPTION_SECRET_KEY" && length($$2) >= 16 { found=1 } END { exit !found }' .env; then \
		generated_key="$$(openssl rand -base64 32)"; \
		env_tmp="$$(mktemp)"; \
		awk -v replacement="$$generated_key" \
			'/^METABASE_ENCRYPTION_SECRET_KEY=/ { print "METABASE_ENCRYPTION_SECRET_KEY=" replacement; next } { print }' \
			.env > "$$env_tmp"; \
		chmod 600 "$$env_tmp"; \
		mv "$$env_tmp" .env; \
		printf '%s\n' 'Generated a private Metabase encryption key in .env'; \
	fi

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

bi-up: bootstrap
	$(COMPOSE) build
	$(MAKE) demo-data
	$(COMPOSE) --profile local --profile bi up -d

metabase-provision: bootstrap
	PYTHONPATH=src python3 -m data_platform.metabase_provision --env-file .env

down:
	$(COMPOSE) --profile local --profile demo --profile bi down

logs:
	$(COMPOSE) logs -f --tail=200

bi-logs:
	$(COMPOSE) --profile bi logs -f --tail=200 metabase metabase-postgres metabase-clickhouse-init

ps:
	$(COMPOSE) --profile local --profile demo --profile bi ps

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

smoke:
	sh scripts/smoke_test.sh

bi-smoke:
	CHECK_METABASE=1 sh scripts/smoke_test.sh

terraform-fmt:
	terraform -chdir=terraform fmt -recursive -check

terraform-validate:
	terraform -chdir=terraform validate

validate:
	$(COMPOSE) --profile local --profile demo --profile bi config --quiet
	python3 -m compileall -q src tests scripts
	terraform -chdir=terraform fmt -recursive -check
