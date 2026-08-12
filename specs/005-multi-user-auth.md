# 005 — Autenticación multiusuario privada

## Estado

Aceptada para una instancia privada de entre 5 y 10 personas.

## Contexto

La credencial HTTP Basic del primer despliegue protege el perímetro, pero no identifica a una
persona ni separa sus datos. La instancia necesita cuentas administradas, sesiones revocables y
ownership explícito antes de permitir más usuarios.

## Objetivos

- Permitir acceso mediante username y contraseña.
- Mantener hábitos, finanzas y gamificación privados por usuario.
- Permitir que un administrador cree, desactive y restablezca cuentas sin ver sus datos.
- Conservar todos los datos actuales bajo el primer administrador.
- Usar una sesión segura y cómoda en Safari móvil.
- Preparar una identidad estable para grupos optativos futuros.

## No objetivos

- Registro público, correo, recuperación automática, OAuth o proveedores sociales.
- Eliminar usuarios o transferir ownership entre cuentas.
- Permisos granulares distintos de `admin` y `member`.
- Grupos, rankings, actividad compartida, perfiles públicos o dashboards sociales.
- Compartir finanzas, notas o nombres de hábitos.
- Múltiples réplicas, Redis o PostgreSQL.

## Modelo

### User

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Identidad estable |
| `username` | string | 3–40, minúsculas; letras ASCII, números, `.`, `_` y `-`; único |
| `display_name` | string | 1–80 caracteres tras recortar |
| `password_hash` | string | Argon2id; nunca se expone |
| `role` | enum | `admin` o `member` |
| `status` | enum | `active` o `disabled` |
| `must_change_password` | boolean | `true` para bootstrap, creación y reset |
| `created_at` | datetime | UTC |
| `updated_at` | datetime | UTC |

La contraseña tiene entre 12 y 128 caracteres. No se imponen reglas arbitrarias de composición.
Username y contraseña inválidos producen el mismo mensaje de acceso para evitar enumeración.

### Session

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Identidad interna |
| `token_hash` | string | SHA-256 hexadecimal único del token opaco |
| `user_id` | integer | Usuario propietario |
| `created_at` | datetime | UTC |
| `expires_at` | datetime | UTC; 14 días después de crearla |

El navegador conserva solo el token aleatorio en `pleno_session`. La cookie es `HttpOnly`,
`SameSite=Strict`, `Path=/` y `Secure` en producción. No se usan JWT ni almacenamiento web.

### Ownership

Los agregados raíz `Habit`, `FinanceSettings`, `Category`, `FinanceTransaction`, `Budget`,
`XpEntry`, `BadgeAward`, `WeeklyChallenge`, `Reward`, `RewardRedemption` y
`FinanceWeeklyReview` pertenecen a un `user_id`. `HabitCheckIn` y `StreakRecovery` heredan
ownership del hábito.

Toda unicidad lógica pasa a ser por usuario: configuración financiera, fuente XP, insignia, semana
de desafío, revisión semanal e idempotencia de canje. Una referencia entre agregados valida que
ambos tengan el mismo propietario.

## Bootstrap y migración

- La migración crea un administrador bloqueado con `id=1` y asigna a esa cuenta todos los datos
  existentes sin cambiar sus IDs.
- `PLANNER_BOOTSTRAP_ADMIN_USERNAME`, `PLANNER_BOOTSTRAP_ADMIN_DISPLAY_NAME` y
  `PLANNER_BOOTSTRAP_ADMIN_PASSWORD` inicializan esa cuenta después de migrar.
- Si la cuenta ya fue inicializada, el bootstrap es idempotente y no modifica la contraseña.
- Si no existe un administrador utilizable y faltan variables, el servicio no inicia.
- Tras validar el acceso, la contraseña bootstrap se elimina de Railway.
- Antes de migrar la base real se crea un snapshot del volumen.

## API de autenticación

- `POST /api/v1/auth/login`
  - Cuerpo: `username`, `password`.
  - `200`: perfil y cookie nueva.
  - `401`: “Usuario o contraseña incorrectos.”
  - `429`: demasiados intentos.
- `POST /api/v1/auth/logout`
  - Invalida la sesión actual, elimina cookie y responde `204`.
- `GET /api/v1/auth/me`
  - Devuelve el perfil actual o `401`.
- `PUT /api/v1/auth/password`
  - Cuerpo: `current_password`, `new_password`.
  - Revoca todas las sesiones, crea una nueva y limpia `must_change_password`.

Los presupuestos de intento, su clave y su cota los define `specs/006-security-hardening.md`. El
límite es local al único proceso y se reinicia al desplegar.

## API administrativa

Solo `admin` puede usar:

- `GET /api/v1/admin/users`: lista metadatos de cuentas, nunca datos de dominio.
- `POST /api/v1/admin/users`: crea cuenta con contraseña temporal; responde `201`.
- `PATCH /api/v1/admin/users/{user_id}`: cambia nombre visible, rol o estado.
- `POST /api/v1/admin/users/{user_id}/password-reset`: establece una contraseña temporal,
  revoca sesiones y responde `204`.

No se puede desactivar la sesión propia, degradar al último administrador activo ni dejar el
sistema sin administrador activo. Las cuentas no se eliminan.

## Autorización

- `/health`, archivos estáticos y rutas SPA son públicos para permitir cargar la pantalla de acceso.
- Toda ruta de dominio exige sesión activa.
- Una cuenta desactivada no puede iniciar sesión y sus sesiones previas dejan de funcionar.
- Mientras `must_change_password=true`, solo se permiten `me`, logout y cambio de contraseña.
- Un recurso ajeno responde `404`, no `403`, y nunca revela su existencia.
- Ser administrador no permite consultar hábitos, gamificación o finanzas ajenas.
- Ningún endpoint de dominio acepta `user_id` desde el cliente.

## CSRF y seguridad

Los controles de perímetro, cabeceras del navegador, límites de uso, política de contraseñas y
registro de eventos se especifican en `specs/006-security-hardening.md`.

- Las mutaciones autenticadas validan que `Origin` sea el mismo origen o un origen local permitido.
- Las contraseñas usan Argon2id mediante `pwdlib[argon2]` y un hash ficticio para usuarios ausentes.
- Los tokens usan al menos 256 bits de entropía y solo se persiste su SHA-256.
- Cambiar o restablecer contraseña y desactivar cuenta revoca sesiones.
- Las sesiones expiradas se eliminan al autenticar o crear sesiones.
- No se registran contraseñas, cookies, hashes, cuerpos financieros ni tokens.

## Estados de interfaz

- **Comprobando sesión:** pantalla estable sin mostrar datos privados.
- **Sin sesión:** formulario de acceso con username y contraseña.
- **Credencial inválida:** mensaje genérico y campos conservados salvo contraseña.
- **Demasiados intentos:** mensaje recuperable sin cuenta regresiva alarmista.
- **Cambio obligatorio:** pantalla dedicada antes de entrar al planificador.
- **Sesión expirada:** vuelve a acceso y explica que debe entrar nuevamente.
- **Cuenta desactivada:** mensaje genérico de acceso; no revela estado a terceros.
- **Administración:** listado, creación, edición, reset y estados de guardado, error y conflicto.

Todos los controles alcanzan 48 × 48 px, conservan foco visible y funcionan desde 320 px.

## Grupos futuros

Una especificación separada podrá añadir `Group` y `GroupMembership` sobre `User.id`. Será
optativa y revocable. Solo podrá compartir proyecciones consentidas de cumplimiento y logros;
finanzas, notas, nombres privados y recursos originales quedan fuera.

No se crean ahora tablas, flags, rutas ni navegación social. Una futura competencia no usará culpa,
pérdida punitiva, urgencia ni participación obligatoria.

## Criterios de aceptación

- Dos usuarios pueden usar IDs y fechas equivalentes sin colisión.
- Un usuario nunca lista, lee, modifica ni elimina datos ajenos, incluso con un ID conocido.
- Finanzas y gamificación se calculan exclusivamente con datos del usuario actual.
- Login, logout, expiración, cambio y reset revocan o rotan sesiones según el contrato.
- Contraseñas y tokens nunca se almacenan en texto plano.
- Solo administradores gestionan cuentas y no obtienen acceso a datos privados.
- La migración conserva IDs y cantidades y asigna el histórico al primer administrador.
- La base limpia y la base migrada producen el mismo esquema final.
- La aplicación sigue funcionando con SQLite, una réplica y el despliegue Railpack existente.

## Decisiones registradas

- **AUTH-001:** usar sesiones opacas persistidas y cookie segura en lugar de JWT.
- **AUTH-002:** aprovisionar cuentas únicamente desde administración.
- **AUTH-003:** usar Argon2id para contraseñas y SHA-256 solo para tokens aleatorios.
- **AUTH-004:** aislar datos en servicios mediante ownership derivado de la sesión.
- **AUTH-005:** asignar todo el histórico al administrador inicial sin alterar IDs.
- **AUTH-006:** mantener al administrador fuera de los datos privados de otras personas.
- **AUTH-007:** diferir grupos y compartir solo proyecciones optativas en una especificación futura.
