# 004 — Primer despliegue

## Estado

Aceptada para la primera instancia personal en Railway, construida con Railpack.

## Contexto

Pleno funciona con React, FastAPI y SQLite en una instancia pequeña compartida por cuentas
administradas. La identidad y el aislamiento se definen en `005-multi-user-auth.md`.

La URL estará disponible en internet. Aunque los datos iniciales no sean sensibles, hábitos y
finanzas no pueden quedar expuestos a lectura o escritura anónima.

## Objetivos

- Construir frontend y backend con Railpack a partir de los lockfiles.
- Servir interfaz y API desde el mismo origen HTTPS.
- Conservar SQLite al reiniciar o desplegar el servicio.
- Exigir una sesión individual antes de mostrar o modificar datos.
- Mantener un procedimiento de Railway corto y verificable.
- No exigir Docker Desktop, una licencia de Docker ni herramientas de contenedores locales.

## No objetivos

- Registro público, recuperación por correo o proveedores externos.
- Aplicación nativa, sincronización sin conexión o notificaciones push.
- PostgreSQL, caché, colas, múltiples réplicas o balanceo.
- Terminar TLS dentro de la aplicación.
- Mantener un Dockerfile, publicar imágenes o usar un registro propio.
- Garantizar despliegues sin interrupción con SQLite.

## Modelo operativo

- La instancia aloja las cuentas administradas definidas en `005-multi-user-auth.md`.
- Railway usa Railpack, un builder abierto, para instalar Node 22, Python 3.11 y `uv`.
- Un servicio ejecuta un proceso Uvicorn y sirve tanto `/api/v1` como el build estático.
- Un volumen se monta en `/data`; la base se guarda en `/data/personal_planner.db`.
- Antes de iniciar Uvicorn se ejecuta `alembic upgrade head`.
- Railway termina HTTPS, asigna el dominio, entrega `PORT` y consulta `/health`.
- La instancia usa una sola réplica. Dos procesos escribiendo el mismo SQLite quedan fuera de
  alcance.

## Configuración

### Valores locales seguros

- `PLANNER_ENVIRONMENT=development`
- `PLANNER_DATABASE_URL=sqlite:///./personal_planner.db`
- `PLANNER_FRONTEND_ORIGINS` limitado a localhost.
- `PLANNER_FRONTEND_DIST` sin definir.
- `PLANNER_ALLOWED_HOSTS` limitado a localhost y clientes de prueba.

### Valores del despliegue

- `PLANNER_ENVIRONMENT=production`
- `PLANNER_DATABASE_URL=sqlite:////data/personal_planner.db`
- `PLANNER_FRONTEND_DIST=/app/frontend/dist`
- `PLANNER_ALLOWED_HOSTS` incluye `*.up.railway.app` y `healthcheck.railway.app`.
- `PLANNER_BOOTSTRAP_ADMIN_*` inicializa el primer administrador y su contraseña se retira después.
- `VITE_API_BASE_URL=/api/v1` se fija durante el build del frontend.

La contraseña bootstrap no tiene valor por defecto, no participa en el build y no se versiona. El
modo producción rechaza el arranque si no existe un administrador utilizable o el build frontend.

## Contrato HTTP

### Público

- `GET /health` devuelve `200` con `{\"status\":\"ok\"}` y no revela configuración ni datos.

### Protegido

- Los archivos SPA y `/api/v1/auth/login` son públicos; las rutas de dominio exigen sesión.
- Sin una sesión válida, la API protegida responde `401`.
- En producción no se publican `/docs`, `/redoc` ni `/openapi.json`.
- Una ruta de interfaz desconocida devuelve el `index.html` para que React Router decida el estado.
- Una ruta desconocida bajo `/api/v1` conserva una respuesta API `404`; nunca devuelve HTML.

## Seguridad mínima

- Contraseñas y cookies solo viajan sobre el HTTPS administrado por Railway.
- Las contraseñas usan Argon2id y los tokens de sesión se persisten únicamente como hash.
- Se validan hosts HTTP contra una lista explícita.
- Todas las respuestas incluyen protección contra sniffing, framing, envío amplio de referrer y
  capacidades del navegador no utilizadas.
- `.env`, bases locales, cachés y dependencias instaladas permanecen excluidos de Git.
- Railpack instala dependencias desde `package-lock.json` y `uv.lock`; las credenciales solo se
  inyectan al ejecutar el servicio.
- Los logs no imprimen encabezados de autorización ni valores de configuración secretos.

Los detalles de cookies, sesiones, bootstrap y autorización se definen en
`005-multi-user-auth.md`.

## Estados de interfaz

- **Sin sesión:** la aplicación muestra su pantalla de acceso.
- **Credencial inválida:** el acceso continúa bloqueado sin revelar si falló el usuario o la clave.
- **Sesión válida:** la aplicación carga únicamente los datos de esa cuenta.
- **Servicio no disponible:** Railway puede reiniciar el proceso según el healthcheck.
- **Ruta profunda:** recargar `/habitos`, `/finanzas` o `/progreso` conserva la pantalla correcta.

No se añade una pantalla propia de inicio de sesión en este incremento.

## Operación y recuperación

- El volumen persiste entre despliegues y reinicios.
- Las migraciones deben poder ejecutarse repetidamente sobre una base actualizada.
- Se recomienda habilitar snapshots del volumen cuando la cuenta de Railway los ofrezca.
- Las cuentas cambian su contraseña dentro de la aplicación; el administrador puede restablecerla.
- Un cambio futuro a Postgres exige una decisión separada basada en concurrencia o necesidades de
  operación observadas.

## Criterios de aceptación

- Railpack ejecuta instalaciones y build desde los lockfiles sin Docker local.
- El servicio escucha en `0.0.0.0:$PORT` y `/health` responde sin autenticación.
- Toda ruta API de dominio responde `401` sin sesión válida.
- Con sesión correcta se cargan la portada, rutas profundas y datos privados de la cuenta.
- El frontend usa `/api/v1` en el mismo origen.
- Una base vacía llega al esquema actual antes de aceptar tráfico.
- Un dato creado permanece después de desplegar de nuevo con el mismo volumen.
- El build local, formato, lint y pruebas existentes continúan pasando.
- El README documenta snapshot, bootstrap del primer administrador, volumen y dominio.

## Decisiones registradas

- **DEP-001:** desplegar frontend y API en un solo servicio y origen.
- **DEP-002:** conservar SQLite en un volumen y limitar la instancia a un proceso y una réplica.
- **DEP-003:** la credencial HTTP Basic compartida queda reemplazada por `AUTH-001` al habilitar
  cuentas administradas.
- **DEP-004:** ejecutar migraciones en el arranque porque el volumen Railway no está disponible
  durante el build ni durante comandos previos al despliegue.
- **DEP-005:** servir el build de React desde FastAPI para evitar un proxy y un segundo servicio.
- **DEP-006:** usar Railpack para construir y ejecutar el servicio sin mantener Docker ni requerir
  herramientas de contenedores locales.
