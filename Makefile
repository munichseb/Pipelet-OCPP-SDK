SHELL := /bin/bash

.PHONY: up down test seed export import

up: ## Startet dev stack
	docker compose up --build

down: ## Stoppt
	docker compose down -v

test: ## Backend Tests
	docker compose exec backend pytest -q

seed: ## Beispiel-Daten
	docker compose exec backend python scripts/seed.py

export: ## Export JSON
	@if [ -z "$$TOKEN" ]; then echo "Set TOKEN env var with a valid Bearer token"; exit 1; fi
	curl -H "Authorization: Bearer $$TOKEN" http://localhost:9200/api/export -o export.json

import: ## Import JSON
	@if [ -z "$$TOKEN" ]; then echo "Set TOKEN env var with a valid Bearer token"; exit 1; fi
	curl -H "Authorization: Bearer $$TOKEN" -X POST -H "Content-Type: application/json" --data @export.json http://localhost:9200/api/import
