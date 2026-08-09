.DEFAULT_GOAL := help

BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_HOST ?= 127.0.0.1
FRONTEND_PORT ?= 5173

.PHONY: help doctor check-ports stop install install-backend install-frontend setup migrate dev dev-backend \
	dev-frontend test test-backend test-frontend lint lint-backend lint-frontend format \
	format-check build check refresh preview preview-backend preview-frontend

help:
	@printf '%s\n' \
		'Personal Planner' \
		'' \
		'  make setup         Instala dependencias y aplica migraciones' \
		'  make dev           Inicia backend y frontend con recarga automática' \
		'  make stop          Detiene los servidores en los puertos configurados' \
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
	@command -v lsof >/dev/null || { echo 'Falta lsof para comprobar puertos locales'; exit 1; }
	@echo 'uv y npm están disponibles.'

check-ports:
	@if lsof -tiTCP:$(BACKEND_PORT) -sTCP:LISTEN >/dev/null; then \
		echo 'El puerto $(BACKEND_PORT) está ocupado. Ejecuta make stop o define BACKEND_PORT.'; \
		exit 1; \
	fi
	@if lsof -tiTCP:$(FRONTEND_PORT) -sTCP:LISTEN >/dev/null; then \
		echo 'El puerto $(FRONTEND_PORT) está ocupado. Ejecuta make stop o define FRONTEND_PORT.'; \
		exit 1; \
	fi

stop:
	@for port in $(BACKEND_PORT) $(FRONTEND_PORT); do \
		pids=$$(lsof -tiTCP:$$port -sTCP:LISTEN); \
		if [ -n "$$pids" ]; then \
			echo "Deteniendo procesos en el puerto $$port: $$pids"; \
			kill -CONT $$pids 2>/dev/null || true; \
			kill -TERM $$pids 2>/dev/null || true; \
		fi; \
	done; \
	for attempt in 1 2 3 4 5 6 7 8 9 10; do \
		busy=0; \
		for port in $(BACKEND_PORT) $(FRONTEND_PORT); do \
			if lsof -tiTCP:$$port -sTCP:LISTEN >/dev/null; then busy=1; fi; \
		done; \
		if [ "$$busy" -eq 0 ]; then exit 0; fi; \
		sleep 0.1; \
	done; \
	for port in $(BACKEND_PORT) $(FRONTEND_PORT); do \
		pids=$$(lsof -tiTCP:$$port -sTCP:LISTEN); \
		if [ -n "$$pids" ]; then \
			echo "Forzando cierre en el puerto $$port: $$pids"; \
			kill -KILL $$pids 2>/dev/null || true; \
		fi; \
	done

install: install-backend install-frontend

install-backend:
	cd $(BACKEND_DIR) && uv sync

install-frontend:
	cd $(FRONTEND_DIR) && npm install

setup: doctor install migrate

migrate:
	cd $(BACKEND_DIR) && uv run alembic upgrade head

dev: check-ports
	@$(MAKE) --no-print-directory -j2 dev-backend dev-frontend

dev-backend:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev -- --host $(FRONTEND_HOST) --port $(FRONTEND_PORT) --strictPort

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
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --host $(BACKEND_HOST) --port $(BACKEND_PORT)

preview-frontend:
	cd $(FRONTEND_DIR) && npm run preview -- --host $(FRONTEND_HOST) --port $(FRONTEND_PORT) --strictPort
