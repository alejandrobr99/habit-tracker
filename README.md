# Personal Planner

Planificador personal centrado en hábitos, finanzas y progreso privado, construido con una
metodología guiada por especificaciones. La primera versión permite registrar hábitos y movimientos,
administrar presupuestos mensuales y reconocer avances sin comparaciones sociales.

## Estructura del monorepo

```text
.
├── Makefile    Comandos locales de instalación, ejecución y calidad
├── backend/    API en Python 3.11, gestionada con uv
├── frontend/   Aplicación web TypeScript, gestionada con npm
├── specs/      Producto, contratos, aceptación y sistema de diseño
└── .cursor/    Regla de trabajo y skill visual del proyecto
```

Las especificaciones vigentes son:

- `specs/constitution.md`: principios de sencillez, robustez y calidad.
- `specs/000-product-foundation.md`: alcance, convenciones y arquitectura del producto.
- `specs/001-habit-tracker.md`: primera funcionalidad completa.
- `specs/002-finance-shell.md`: estructura inicial del módulo financiero.
- `specs/003-gamification.md`: progreso, insignias, desafíos y recompensas privadas.
- `specs/004-finance-mvp.md`: movimientos, categorías, presupuestos y resumen mensual.
- `specs/design-system.md`: lenguaje visual, componentes y accesibilidad.
- `specs/development-readiness.md`: controles mínimos y decisiones diferidas.

## Método de trabajo

1. Leer fundamentos, sistema de diseño y la especificación de la función.
2. Actualizar la especificación si cambia el comportamiento esperado.
3. Implementar el incremento sin ampliar su alcance.
4. Verificar modelo, API, estados de UI y criterios de aceptación.
5. Registrar decisiones duraderas en la especificación afectada.

La regla `.cursor/rules/spec-driven.mdc` mantiene este flujo. La skill
`.cursor/skills/planner-design/SKILL.md` guía la creación y revisión de interfaces.

## Comandos rápidos

Desde la raíz del repositorio:

```bash
make setup
make dev
```

`make setup` instala dependencias y aplica las migraciones. `make dev` inicia backend y frontend
en paralelo con recarga automática. La aplicación queda disponible en `http://localhost:5173` y
la documentación de la API en `http://localhost:8000/docs`. Usa `Ctrl+C` para detener ambos
procesos.

Para validar cambios:

```bash
make check
```

Otros comandos útiles:

```bash
make help       # Lista todos los comandos
make test       # Pruebas de backend y frontend
make lint       # Ruff y Oxlint
make format     # Formatea Python con Ruff
make refresh    # Dependencias, migraciones y verificación completa
make preview    # Build de frontend y servidores sin recarga automática
```

## Backend

Desde la raíz:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

La API queda disponible en `http://localhost:8000`, con salud en `/health`, documentación en
`/docs` y recursos del planner bajo `/api/v1`. Copia `backend/environment.example` a
`backend/.env` para cambiar los parámetros de ejecución.

Para verificar el backend:

```bash
cd backend
uv run pytest
uv run ruff format --check .
uv run ruff check .
```

## Frontend

En otra terminal, desde la raíz:

```bash
cd frontend
npm install
npm run dev
```

La aplicación queda disponible en `http://localhost:5173`. Copia
`frontend/environment.example` a `frontend/.env` para usar otra API.

Para verificar el frontend:

```bash
cd frontend
npm run lint
npm test
npm run build
```

La integración continua repite estos controles y comprueba que la migración de Alembic pueda crear
el esquema desde cero.

## Prueba local en cinco minutos

Inicia el backend y el frontend en dos terminales con los comandos anteriores. Después abre
`http://localhost:5173` y recorre este flujo:

1. En **Hábitos**, crea un hábito de tipo “Construir” o “Evitar” y registra el cumplimiento de hoy.
2. En **Progreso**, comprueba el XP, crea un desafío semanal y configura una recompensa personal.
3. En **Finanzas**, elige COP, USD o EUR como moneda base.
4. Crea una categoría de gasto y otra de ingreso, y registra un movimiento de cada tipo.
5. Configura un presupuesto para la categoría de gasto y verifica el resumen del mes.
6. Regresa a **Progreso** para revisar la insignia y marcar la revisión financiera semanal.

Los datos se guardan en `backend/personal_planner.db`. Para probar con una base aislada, define
`PLANNER_DATABASE_URL=sqlite:///./planner_test.db` antes de ejecutar Alembic y Uvicorn. La moneda
base solo puede cambiar mientras no existan movimientos ni presupuestos.
