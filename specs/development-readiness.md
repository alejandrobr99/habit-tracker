# Preparación para la primera versión

## Evaluación crítica

La arquitectura elegida es adecuada para un producto personal: un frontend, una API y SQLite.
Separar más servicios no aportaría valor ahora. Los riesgos iniciales no son de escala, sino de
contratos inconsistentes, configuración implícita y falta de verificación automática.

## Bloqueadores antes de desarrollar funciones nuevas

- [ ] Alinear exactamente nombres, métodos y cuerpos entre la spec, OpenAPI y los tipos frontend.
- [ ] Mantener una migración reproducible y probar que una base vacía puede llegar al esquema actual.
- [x] Documentar variables en archivos `environment.example`, con valores locales seguros.
- [ ] Ejecutar en CI formato, lint, tipos, pruebas backend, pruebas frontend y build.
- [ ] Medir cobertura de reglas de dominio y recorridos críticos sin perseguir un porcentaje vacío.
- [ ] Probar al menos creación, edición, archivo, check-in idempotente, eliminación y cálculo de racha.
- [ ] Probar en frontend estados vacío, error y flujo principal con la API simulada.
- [ ] Confirmar navegación y diálogos con teclado, foco visible y ancho móvil.

## Configuración mínima

### Backend

- Python 3.11 como versión mínima.
- `uv.lock` versionado y `uv sync --frozen` en CI.
- Ruff como formatter e inspector único.
- pytest, pytest-cov y TestClient para contratos HTTP.
- Alembic como único mecanismo de cambio de esquema.
- Configuración por `PLANNER_DATABASE_URL`, `PLANNER_API_PREFIX` y
  `PLANNER_FRONTEND_ORIGINS`.
- El despliegue personal añade la configuración validada definida en `004-deployment.md`.

### Frontend

- `package-lock.json` versionado y `npm ci` en CI.
- TypeScript estricto, Oxlint, Vitest y Testing Library.
- `VITE_API_BASE_URL` como única variable obligatoria.
- Tokens CSS versionados para personalización visual.

## Parámetros que no deben existir todavía

- Proveedor de caché, tamaño de pool, colas o workers.
- Estrategias intercambiables de repositorio o motor de reglas.
- Flags para funciones que aún no están implementadas.
- Temas completos por usuario antes de validar el sistema de tokens.
- Límites de paginación mientras las colecciones sean pequeñas.

## Pruebas robustas, no numerosas por inercia

Una prueba aporta valor si protege una regla observable. La suite inicial debe concentrarse en:

1. Reglas temporales: cambio de semana, día incompleto y rachas diarias o semanales.
2. Integridad: un solo check-in por hábito y fecha, archivo sin pérdida de historial.
3. Contrato: códigos HTTP, validación y serialización de fechas con zona.
4. Interfaz: mutación correcta, actualización visible y recuperación ante error.
5. Migración: creación limpia del esquema desde cero.

Los detalles de implementación privados se prueban a través de su comportamiento público. No se
usan mocks en reglas puras; los límites HTTP y navegador sí pueden simularse.

## Diferido con intención

- PostgreSQL, Redis, tareas en segundo plano y observabilidad remota.
- Sincronización offline.
- SDK generado desde OpenAPI; se reconsiderará cuando el contrato crezca.
- Pruebas end-to-end en navegador; se añadirán cuando exista un flujo de versión desplegable.

## Primer despliegue

El servicio único construido con Railpack, el volumen SQLite y la configuración Railway se definen
en `004-deployment.md`. Las cuentas administradas, sesiones y aislamiento se definen en
`005-multi-user-auth.md`.
