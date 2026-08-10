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
- `specs/004-deployment.md`: Railpack y despliegue privado.
- `specs/005-multi-user-auth.md`: cuentas, sesiones y aislamiento por persona.
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

`make setup` instala dependencias y aplica las migraciones. `make dev` comprueba que los puertos
estén libres e inicia backend y frontend en paralelo con recarga automática. La aplicación queda
disponible en `http://127.0.0.1:5173` y la documentación de la API en
`http://127.0.0.1:8000/docs`. Usa `Ctrl+C` para detener ambos procesos.

Los puertos y hosts son parametrizables:

```bash
make dev BACKEND_PORT=8100 FRONTEND_PORT=5100
make stop
```

`make stop` termina únicamente los procesos que escuchan en los puertos configurados. El frontend
también admite `VITE_API_BASE_URL` y `VITE_API_TIMEOUT_MS`; consulta `frontend/environment.example`.

Para validar cambios:

```bash
make check
```

Otros comandos útiles:

```bash
make help       # Lista todos los comandos
make stop       # Libera los puertos locales configurados
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

## Primer despliegue en Railway

Railway usa `railpack.json` para instalar Node 22, Python 3.11 y `uv`, construir React y ejecutar
FastAPI. Railpack es abierto y no requiere Docker Desktop, una licencia de Docker ni instalar una
herramienta adicional.

El despliegue requiere un servicio, un volumen y las variables temporales del primer administrador:

1. Crea un proyecto en Railway y conecta este repositorio de GitHub. Railway detectará
   `railpack.json` y `railway.json`.
2. Añade un volumen al servicio y usa exactamente `/data` como ruta de montaje. Mantén una sola
   réplica porque la instancia usa SQLite.
3. Antes de desplegar esta migración sobre datos existentes, crea un snapshot del volumen.
4. En **Variables**, define `PLANNER_BOOTSTRAP_ADMIN_USERNAME`,
   `PLANNER_BOOTSTRAP_ADMIN_DISPLAY_NAME` y `PLANNER_BOOTSTRAP_ADMIN_PASSWORD`. Usa una
   contraseña de al menos 12 caracteres, única y no versionada.
5. En **Networking**, selecciona **Generate Domain**. Railway publicará el servicio con HTTPS y
   comprobará `/health` antes de dirigir tráfico.

No necesitas configurar `PORT`, la URL de SQLite, CORS ni la URL de la API: `railpack.json` ya
declara los valores no secretos correctos para Railway. El comando de arranque aplica las
migraciones antes de iniciar Uvicorn. Si luego añades un dominio propio, incorpora su host a
`PLANNER_ALLOWED_HOSTS`, por ejemplo
`["*.up.railway.app","healthcheck.railway.app","habit-tracker.co","www.habit-tracker.co"]`.

En el iPhone, abre la dirección `https://...up.railway.app` en Safari, entra con el administrador y
cambia la contraseña temporal. Después elimina las tres variables `PLANNER_BOOTSTRAP_ADMIN_*` de
Railway; los siguientes despliegues conservan la cuenta en SQLite. Desde **Administración** puedes
crear entre 5 y 10 cuentas, asignar una contraseña temporal, desactivar accesos y restablecer
claves. Cada persona debe cambiar su clave al entrar y solo ve sus propios datos.

Puedes usar **Compartir → Añadir a pantalla de inicio** para tener un acceso directo. Mantén una
sola réplica, habilita snapshots del volumen y restaura el snapshot si la migración inicial falla.

## Prueba local en cinco minutos

Inicia el backend y el frontend con los comandos anteriores. Después abre
`http://127.0.0.1:5173`, entra con `admin` / `pleno-local-2026`, cambia esa clave local y recorre
este flujo:

1. En **Hábitos**, crea un hábito de tipo “Construir” o “Evitar” y registra el cumplimiento de hoy.
2. En **Progreso**, comprueba el XP, crea un desafío semanal y configura una recompensa personal.
3. En **Finanzas**, elige COP, USD o EUR como moneda base.
4. Crea una categoría de gasto y otra de ingreso, y registra un movimiento de cada tipo.
5. Configura un presupuesto para la categoría de gasto y verifica el resumen del mes.
6. Regresa a **Progreso** para revisar la insignia y marcar la revisión financiera semanal.

Los datos se guardan en `backend/personal_planner.db`. Para probar con una base aislada, define
`PLANNER_DATABASE_URL=sqlite:///./planner_test.db` antes de ejecutar Alembic y Uvicorn. La moneda
base solo puede cambiar mientras no existan movimientos ni presupuestos.
