.DEFAULT_GOAL := help

BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: help doctor install install-backend install-frontend setup migrate dev dev-backend \
	dev-frontend test test-backend test-frontend lint lint-backend lint-frontend format \
	format-check build check refresh preview preview-backend preview-frontend

help:
	@printf '%s\n' \
		'Personal Planner' \
		'' \
		'  make setup         Instala dependencias y aplica migraciones' \
		'  make dev           Inicia backend y frontend con recarga automática' \
		'  make test          Ejecuta todas las pruebas' \
		'  make lint          Ejecuta los linters' \
		'  make format        Formatea el backend con Ruff' \
		'  make build         Construye el frontend para producción' \
		'  make check         Ejecuta formato, lint, pruebas y build' \
		'  make refresh       Actualiza dependencias, migra y verifica todo' \
		'  make preview       Sirve el build y la API sin modo reload' \
		'  make doctor        Comprueba las herramientas requeridas'

doctor:
	@command -v uv >/dev/null || { echo 'Falta uv: https://docs.astral.sh/uv/'; exit 1; }
	@command -v npm >/dev/null || { echo 'Falta npm: instala Node.js 22 o superior'; exit 1; }
	@echo 'uv y npm están disponibles.'

install: install-backend install-frontend

install-backend:
	cd $(BACKEND_DIR) && uv sync

install-frontend:
	cd $(FRONTEND_DIR) && npm install

setup: doctor install migrate

migrate:
	cd $(BACKEND_DIR) && uv run alembic upgrade head

dev:
	@$(MAKE) --no-print-directory -j2 dev-backend dev-frontend

dev-backend:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

test:
	@$(MAKE) --no-print-directory -j2 test-backend test-frontend

test-backend:
	cd $(BACKEND_DIR) && uv run pytest

test-frontend:
	cd $(FRONTEND_DIR) && npm test

lint:
	@$(MAKE) --no-print-directory -j2 lint-backend lint-frontend

lint-backend:
	cd $(BACKEND_DIR) && uv run ruff check .

lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint

format:
	cd $(BACKEND_DIR) && uv run ruff format .

format-check:
	cd $(BACKEND_DIR) && uv run ruff format --check .

build:
	cd $(FRONTEND_DIR) && npm run build

check: format-check lint test build

refresh: install migrate check

preview: build migrate
	@$(MAKE) --no-print-directory -j2 preview-backend preview-frontend

preview-backend:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app

preview-frontend:
	cd $(FRONTEND_DIR) && npm run preview -- --host 0.0.0.0
