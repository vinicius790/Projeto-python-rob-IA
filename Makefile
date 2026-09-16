.PHONY: install test coverage lint format typecheck audit check run migrate seed docker-up docker-down build

install:
	python -m pip install -e ".[dev,ml,postgres]"

test:
	pytest

coverage:
	pytest --cov=robia_ops --cov-report=term-missing --cov-report=xml --cov-fail-under=88

lint:
	ruff check src tests

format:
	ruff format src tests

typecheck:
	mypy src/robia_ops

audit:
	pip-audit

check: lint typecheck coverage
	python -m compileall -q src tests alembic

run:
	robia serve --reload

migrate:
	alembic upgrade head

seed:
	robia seed-demo

docker-up:
	docker compose up --build

docker-down:
	docker compose down

build:
	python -m build
