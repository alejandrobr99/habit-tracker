# 006 — Endurecimiento de seguridad

## Estado

Aceptada. Corrige defectos de seguridad de la instancia actual y fija el contrato de controles que
toda función nueva debe respetar, incluido el módulo futuro de OCR y modelo de lenguaje.

## Contexto

`specs/005-multi-user-auth.md` definió identidad, sesiones y aislamiento por propietario. La
implementación resultante es sólida en credenciales y ownership, pero la revisión de seguridad
encontró controles ausentes o anulados por la configuración de despliegue.

El hallazgo principal es que el límite de intentos de acceso no protege nada en producción: el
servidor confía en la cabecera `X-Forwarded-For` de cualquier origen, y como el límite se calcula
por IP, cambiar esa cabecera en cada petición devuelve un presupuesto de intentos nuevo. Además, la
estructura que cuenta los fallos crece sin cota, por lo que esos mismos intentos consumen memoria de
forma indefinida.

La instancia también aceptará pronto archivos de estado de cuenta y recibos para extraer movimientos
con OCR y un modelo de lenguaje. Eso introduce contenido hostil que se interpreta, coste por
petición y un componente que no distingue instrucciones de datos. Los límites de tamaño y frecuencia
que hoy faltan son requisito previo de ese módulo, no un detalle posterior.

## Objetivos

- Cerrar los defectos de seguridad encontrados en autenticación, disponibilidad y navegador.
- Hacer que el límite de intentos sea efectivo aunque el atacante controle la IP declarada.
- Acotar el coste que una petición anónima puede imponer al servicio.
- Contener el impacto de contenido malicioso que llegue a mostrarse en la interfaz.
- Dejar evidencia de eventos de seguridad sin registrar datos personales ni financieros.
- Detectar dependencias vulnerables y secretos filtrados antes de desplegar.
- Fijar los controles que el módulo de OCR y modelo de lenguaje deberá cumplir.

## No objetivos

- WAF, pasarela de IA, Redis, cola de trabajos, múltiples réplicas o base de datos distinta.
- Segundo factor, claves de acceso, OAuth, correo o recuperación automática de contraseña.
- Cifrado de la base en reposo; el volumen del proveedor queda fuera del modelo de amenaza.
- Detección de intrusiones, alertas automáticas o retención de registros a largo plazo.
- Implementar ahora la carga de archivos, el OCR o la llamada al modelo.
- Reescribir el contrato de errores existente ni introducir códigos de error propios.

## Modelo de amenaza

| Actor | Capacidad asumida | Control principal |
| --- | --- | --- |
| Anónimo en internet | Peticiones ilimitadas con cualquier cabecera y cualquier cuerpo | Límite por cuenta, límite por IP derivada, tamaño máximo de cuerpo |
| Titular de cuenta | Sesión válida y conocimiento de identificadores ajenos | Ownership derivado de la sesión y respuesta `404` |
| Sitio de terceros | Ejecutar peticiones desde el navegador de la víctima | `SameSite=Strict`, validación de `Origin`, CORS explícito |
| Contenido subido | Archivo o texto que el servidor interpreta | Validación por contenido, cotas de recurso y confirmación humana |
| Cadena de suministro | Dependencia vulnerable o secreto filtrado | Lockfile, escaneo de dependencias y de secretos |

Queda fuera: acceso físico al volumen, ruptura de Argon2id o TLS, y amenazas internas del proveedor.

## Defectos corregidos

| Id | Severidad | Defecto | Corrección |
| --- | --- | --- | --- |
| SEC-F01 | Alta | El servicio confía en `X-Forwarded-For` de cualquier origen, por lo que la IP del cliente es arbitraria y el límite de intentos se anula cambiando una cabecera | La IP se deriva de un número declarado de proxies del despliegue; el límite deja de depender solo de la IP |
| SEC-F02 | Alta | El registro de fallos de acceso crea una entrada por cada combinación consultada y nunca la libera, incluso sin fallos | Registro acotado con desalojo, sin crear entradas al consultar |
| SEC-F03 | Alta | Ninguna ruta limita el tamaño del cuerpo, incluidas las anónimas | Tamaño máximo verificado por cabecera y por bytes recibidos |
| SEC-F04 | Media | Sin `Content-Security-Policy`, el contenido inyectado no encuentra ninguna contención en el navegador | Política restrictiva sin `unsafe-inline` ni `unsafe-eval` |
| SEC-F05 | Media | Sin `Strict-Transport-Security`, una primera petición en claro es interceptable | Cabecera presente en producción |
| SEC-F06 | Media | Solo el acceso tiene límite; adivinar la contraseña actual desde una sesión válida es ilimitado | Límite de cambios de contraseña por cuenta |
| SEC-F07 | Media | CORS permite cualquier método y cualquier cabecera junto con credenciales | Métodos y cabeceras declarados explícitamente |
| SEC-F08 | Media | Las respuestas de la API no impiden ser almacenadas en caché | `Cache-Control: no-store` en la API |
| SEC-F09 | Media | Ningún evento de seguridad queda registrado | Registro de eventos sin datos sensibles |
| SEC-F10 | Media | La integración continua no detecta dependencias vulnerables ni secretos | Escaneo de dependencias, de secretos y reglas estáticas de seguridad |
| SEC-F11 | Baja | Una contraseña de longitud válida puede ser el propio username o un valor trivial | Rechazo de contraseñas triviales o derivadas del username |
| SEC-F12 | Baja | Los esquemas de identidad aceptan campos no declarados | Campos no declarados rechazados en identidad y administración |

## Modelo

### Origen de la petición

La IP del cliente se deriva así:

- Si el despliegue declara `n = 0` proxies, la IP es la de la conexión.
- Si declara `n >= 1`, la IP es la entrada en la posición `n` contando desde la derecha de
  `X-Forwarded-For`, porque cada proxy añade al final y solo las `n` últimas entradas son
  verificables. Las anteriores las controla el cliente.
- Si `X-Forwarded-For` falta o tiene menos entradas que `n`, se usa la entrada más a la izquierda
  disponible o, en su ausencia, la IP de la conexión.

Ningún valor derivado de la petición se usa como única identidad para decidir un límite.

### Presupuestos de intento

| Presupuesto | Clave | Máximo | Ventana | Efecto al agotarse |
| --- | --- | --- | --- | --- |
| Acceso por cuenta | Username normalizado | 5 | 15 min | `429` en `POST /auth/login` |
| Acceso por origen | IP derivada | 20 | 15 min | `429` en `POST /auth/login` |
| Cambio de contraseña | Identificador de cuenta | 5 | 15 min | `429` en `PUT /auth/password` |

El presupuesto por cuenta hace que rotar la IP no restablezca el intento. El presupuesto por origen
evita que una sola IP recorra muchas cuentas. Un acceso correcto limpia los presupuestos de esa
cuenta y de esa IP.

El registro de intentos conserva como máximo 2048 claves. Al alcanzar el máximo se descartan primero
las entradas cuya ventana ya venció y, si no basta, las más antiguas. Consultar un presupuesto nunca
crea una entrada. El registro es local al único proceso y se reinicia al desplegar.

### Tamaño de petición

El máximo de cuerpo es 64 KiB, suficiente para todo contrato actual, cuyo campo mayor es una nota de
500 caracteres. Se verifica en dos momentos:

- Antes de leer el cuerpo, si `Content-Length` lo declara.
- Mientras se reciben los bytes, para cubrir peticiones sin longitud declarada o que declaran menos
  de lo que envían.

Superar el máximo produce `413` sin leer el resto de la petición. El módulo de OCR definirá su
propio máximo en su especificación; no reutilizará este valor.

### Contraseñas

Además de la longitud de 12 a 128 caracteres ya especificada, se rechaza una contraseña que:

- contenga el username, o esté contenida en él, ignorando mayúsculas;
- coincida, ignorando mayúsculas, con un valor de una lista corta de contraseñas frecuentes;
- use menos de cinco caracteres distintos, lo que descarta repeticiones y patrones cortos.

No se añaden reglas de composición: no se exige mayúscula, dígito ni símbolo. La validación se
aplica en cambio de contraseña, creación administrativa, restablecimiento administrativo e
inicialización del primer administrador.

## Cabeceras del navegador

Toda respuesta, incluidas las de error, lleva:

| Cabecera | Valor | Motivo |
| --- | --- | --- |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'` | Contiene inyección de contenido |
| `X-Content-Type-Options` | `nosniff` | Evita interpretar un tipo distinto al declarado |
| `X-Frame-Options` | `DENY` | Compatibilidad con clientes sin CSP |
| `Referrer-Policy` | `no-referrer` | Evita filtrar rutas a terceros |
| `Permissions-Policy` | `camera=(), geolocation=(), microphone=()` | Niega capacidades no usadas |
| `Cross-Origin-Opener-Policy` | `same-origin` | Aísla el contexto de navegación |
| `Cross-Origin-Resource-Policy` | `same-origin` | Evita inclusión desde otro origen |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` solo en producción | Fuerza HTTPS tras la primera visita |

La construcción del frontend no emite script ni estilo en línea, por lo que la política no necesita
`unsafe-inline`, `unsafe-eval`, nonce ni hash. Un cambio que introduzca estilo o script en línea es
un defecto: debe resolverse en el frontend, no relajando la política. No se solicita `preload` de
HSTS porque es difícil de revertir.

Las respuestas bajo el prefijo de la API llevan además `Cache-Control: no-store`, porque contienen
datos privados. Los archivos estáticos conservan su comportamiento de caché.

## CORS

Se declaran explícitamente los métodos `GET`, `POST`, `PUT`, `PATCH`, `DELETE` y `OPTIONS`, y la
cabecera `Content-Type`. Los orígenes siguen viniendo de configuración y en producción la lista está
vacía porque la API y el frontend comparten origen. Las credenciales se permiten solo para los
orígenes declarados; nunca con comodín.

## Registro de eventos

Se emite un evento por cada suceso relevante, con nombre estable y campos acotados:

`login_succeeded`, `login_failed`, `login_rate_limited`, `session_rejected`, `password_changed`,
`password_change_rate_limited`, `admin_user_created`, `admin_user_updated`,
`admin_password_reset`, `request_origin_rejected`, `request_too_large`.

Cada evento puede incluir `event`, `outcome`, `username`, `user_id`, `client_ip`, `method`, `path`
y `reason`. Nunca incluye contraseñas, tokens, cookies, hashes, importes, descripciones, notas,
contenido de archivos ni cuerpos de petición.

## Cadena de suministro

- La integración continua ejecuta reglas estáticas de seguridad sobre el backend, escaneo de
  dependencias del backend y del frontend, y escaneo de secretos del repositorio.
- Una vulnerabilidad de severidad alta o superior detiene la integración.
- Las actualizaciones de dependencias llegan por propuestas automáticas semanales.
- Los permisos concedidos a la integración continua son de solo lectura del contenido.

## Configuración

| Variable | Valor local | Producción | Regla |
| --- | --- | --- | --- |
| `PLANNER_TRUSTED_PROXY_HOPS` | `0` | `1` | Entero de 0 a 4; número de proxies que añaden `X-Forwarded-For` |
| `PLANNER_MAX_REQUEST_BYTES` | `65536` | `65536` | Entero de 1 KiB a 1 MiB |

El servidor de aplicación no confía en cabeceras de proxy de origen arbitrario. La derivación de la
IP es responsabilidad de la aplicación, con el número de saltos declarado.

## API

Los contratos existentes no cambian de forma ni de nombre. Se añaden estas respuestas:

- `413` cuando el cuerpo supera el máximo, con `detail` genérico.
- `429` en `PUT /api/v1/auth/password` al agotar el presupuesto de cambios.
- `422` cuando una contraseña nueva es trivial o derivada del username.
- Los esquemas de identidad y administración responden `422` ante un campo no declarado.

## Estados de interfaz

- **Demasiados intentos:** mensaje recuperable, sin cuenta regresiva alarmista, en acceso y en
  cambio de contraseña.
- **Contraseña rechazada:** explica el motivo concreto sin sugerir reglas de composición ni revelar
  la lista de valores frecuentes.
- **Petición demasiado grande:** mensaje cercano al contenido que indica reducir el tamaño.
- Ningún estado nuevo revela existencia de cuentas, estado de otras personas ni detalle interno.

## Módulo futuro de OCR y modelo de lenguaje

Este apartado fija el contrato mínimo que la especificación de ese módulo deberá cumplir. No habilita
nada todavía.

### Recepción del archivo

- Solo con sesión activa, con límite de trabajos por cuenta aplicado antes de leer el cuerpo.
- Formatos aceptados por contenido, no por extensión ni por `Content-Type`: JPEG, PNG y PDF.
- Máximo propio de tamaño, de páginas y de dimensiones, verificado antes de decodificar por completo.
- Se rechazan archivos comprimidos, formatos ofimáticos, SVG y HTML.
- Se rechaza un PDF con JavaScript, acciones automáticas, formularios o archivos incrustados.
- El nombre de almacenamiento lo genera el servidor; el nombre recibido nunca construye una ruta.
- El archivo se guarda fuera de todo directorio servido y sin permiso de ejecución, o no se guarda.
- Se define plazo de eliminación y pertenencia verificada en la consulta para cualquier descarga.

### Tratamiento del contenido

- El texto extraído es entrada de usuario: se valida, se acota y se escapa al presentarlo.
- La extracción se ejecuta con tiempo y memoria máximos, y su agotamiento es un fallo normal.
- El contenido del archivo y el texto extraído nunca se registran.

### Uso del modelo

- El modelo es un transformador de texto sin privilegios: no decide, no persiste, no ejecuta
  acciones y no recibe herramientas.
- Las instrucciones del sistema y el contenido no confiable viajan en canales separados y marcados.
- La respuesta debe cumplir un esquema estricto validado por código determinista; una respuesta que
  no lo cumple se descarta sin intentar repararla.
- Los campos propuestos pasan la misma validación que la captura manual, incluida la pertenencia de
  la categoría al usuario actual.
- Ninguna propuesta se persiste sin confirmación explícita de la persona.
- El contexto enviado no contiene secretos, identificadores internos ni datos de otras cuentas.
- Se acota el número de trabajos por cuenta y por instancia, y el tamaño de la entrada.
- Se registra identificador de trabajo, resultado, duración y motivo de fallo; nunca el contenido.
- Que el análisis salga de la instancia hacia un proveedor externo es una decisión de privacidad que
  la especificación del módulo debe registrar y la interfaz debe hacer explícita.

## Criterios de aceptación

- Cinco fallos de acceso para una cuenta producen `429` aunque cada intento declare una IP distinta.
- Veinte fallos desde una misma IP derivada producen `429` aunque usen cuentas distintas.
- Un acceso correcto restablece los presupuestos de esa cuenta y de esa IP.
- Consultar el estado de un presupuesto no aumenta el tamaño del registro de intentos.
- El registro de intentos no supera su cota tras muchas claves distintas.
- Con un proxy declarado, la IP derivada es la última entrada de `X-Forwarded-For` y no la primera.
- Sin proxies declarados, la IP derivada es la de la conexión y `X-Forwarded-For` se ignora.
- Un cuerpo mayor al máximo responde `413`, tanto declarando `Content-Length` como sin declararlo.
- Un cuerpo dentro del máximo sigue funcionando en todos los contratos existentes.
- Toda respuesta, incluidas `401`, `403`, `404`, `413`, `422` y `429`, lleva las cabeceras definidas.
- `Strict-Transport-Security` aparece en producción y no en desarrollo.
- Las respuestas de la API llevan `Cache-Control: no-store`.
- La política de contenido no contiene `unsafe-inline` ni `unsafe-eval`.
- La construcción del frontend no emite script ni estilo en línea.
- Seis cambios de contraseña fallidos para una cuenta producen `429`.
- Una contraseña igual al username, contenida en él, frecuente o de menos de cinco caracteres
  distintos responde `422` en cambio, creación y restablecimiento.
- Un campo no declarado en un cuerpo de identidad o administración responde `422`.
- Los eventos definidos se emiten con su nombre estable y sin datos sensibles.
- La integración continua falla ante una dependencia vulnerable de severidad alta o un secreto.
- La aplicación sigue funcionando con SQLite, una réplica y el despliegue Railpack existente.
- El escaneo de secretos ignora únicamente el detector `Lob`, cuya coincidencia actual con nombres
  de pruebas `test_` fue verificada como falso positivo; los demás detectores siguen en modo
  `verified` y bloquean la integración.

## Decisiones registradas

- **SEC-001:** derivar la IP del cliente en la aplicación mediante un número declarado de proxies, y
  no confiar en cabeceras de proxy de origen arbitrario en el servidor de aplicación.
- **SEC-002:** limitar los intentos por cuenta además de por origen, para que rotar la IP no
  restablezca el presupuesto.
- **SEC-003:** acotar y desalojar todo registro en memoria alimentado por entrada anónima.
- **SEC-004:** verificar el tamaño del cuerpo por cabecera y por bytes recibidos, con un máximo
  global pequeño y máximos propios por módulo cuando exista una necesidad real.
- **SEC-005:** mantener una política de contenido sin `unsafe-inline`, tratando cualquier necesidad
  de estilo o script en línea como defecto del frontend.
- **SEC-006:** conservar el nombre de cookie actual en lugar de adoptar el prefijo `__Host-`, porque
  `HttpOnly`, `SameSite=Strict`, `Secure` y `Path=/` ya cubren la amenaza y el cambio invalidaría
  las sesiones vigentes sin beneficio proporcional.
- **SEC-007:** conservar la expiración absoluta de 14 días sin inactividad ni renovación, para no
  escribir en la base en cada petición con SQLite y una réplica.
- **SEC-008:** registrar eventos de seguridad como texto estructurado del proceso, sin almacenarlos
  en la base ni añadir servicios de observabilidad.
- **SEC-009:** tratar el modelo de lenguaje como transformador sin privilegios cuya salida siempre
  requiere validación determinista y confirmación humana.
- **SEC-010:** mantener el escaneo de dependencias y secretos en integración continua en lugar de
  auditorías manuales periódicas.
- **SEC-011:** excluir únicamente el detector `Lob` del escaneo de secretos porque su implementación
  actual confunde nombres de pruebas con claves `test_`; revisar la excepción si cambia el patrón
  del detector o aparecen credenciales Lob reales.

## Preguntas abiertas

- ¿El módulo de OCR usará un proveedor externo o extracción local, y qué implica para privacidad?
- ¿Cuándo el número de personas justificará segundo factor o claves de acceso?
