.PHONY: install lint format typecheck test migrate up down

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

migrate:
	cd backend && alembic upgrade head

up:
	docker compose up --build

down:
	docker compose down

