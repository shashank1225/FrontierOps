.PHONY: install lint format typecheck test frontend-check gate migrate up up-ai down logs

install:
	python -m pip install -e "./backend[dev]"

lint:
	python -m ruff check backend

format:
	python -m ruff format backend

typecheck:
	python -m mypy backend

test:
	python -m pytest backend/tests

frontend-check:
	cd frontend && npm run lint && npm run typecheck && npm test

gate:
	cd backend && python -m evaluation.ci_gate --suite evaluation/ci_suite.json --report artifacts/ci-evaluation-report.json

migrate:
	cd backend && alembic upgrade head

up:
	docker compose up --build

up-ai:
	docker compose --profile ai up --build

down:
	docker compose down

logs:
	docker compose logs --follow api worker frontend
