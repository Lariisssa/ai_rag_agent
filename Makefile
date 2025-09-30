SHELL := /bin/bash

.PHONY: dev fmt test migrate eval backend-req frontend-install

dev:
	docker-compose up --build

fmt:
	docker-compose run --rm backend bash -lc "ruff check --fix . && black . && mypy --strict backend/app"
	docker-compose run --rm frontend sh -lc "pnpm prettier --write . && pnpm eslint . --fix"

test:
	docker-compose run --rm backend bash -lc "pytest -q"
	docker-compose run --rm frontend sh -lc "pnpm test"

migrate:
	docker-compose run --rm backend bash -lc "alembic upgrade head"

eval:
	docker-compose run --rm backend bash -lc "python -m evaluation.run"

backend-req:
	docker-compose run --rm backend bash -lc "pip install -r requirements.txt"

frontend-install:
	docker-compose run --rm frontend sh -lc "pnpm install"
