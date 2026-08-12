---
name: planner-security
description: Diseña, implementa y revisa controles de seguridad del planificador con criterio de amenaza real y sin infraestructura anticipada. Se usa automáticamente al trabajar con autenticación, sesiones, cookies, contraseñas, autorización, límites de uso, cabeceras del navegador, cargas de archivos, OCR, integraciones con modelos de lenguaje, secretos, despliegue o dependencias.
---

# Seguridad del planificador

## Fuente de verdad

Lee antes de trabajar:

1. `specs/006-security-hardening.md` para el contrato de controles vigente.
2. `specs/005-multi-user-auth.md` para identidad, sesiones y aislamiento por propietario.
3. `specs/constitution.md` para robustez proporcional y parametrización con propósito.
4. `specs/000-product-foundation.md` para privacidad local y minimización de datos.
5. [REFERENCE.md](REFERENCE.md) para cargas de archivos, OCR y modelos de lenguaje.

Si un control necesario no está especificado, actualiza la especificación antes de escribirlo en
código. Un control sin criterio de aceptación observable no está terminado.

## Modelo de amenaza vigente

Diseña contra estos adversarios y no contra otros:

- **Anónimo en internet:** encuentra la URL pública e intenta entrar, enumerar cuentas, agotar
  memoria o CPU, y descubrir rutas internas.
- **Titular de cuenta:** intenta leer o modificar datos de otra persona manipulando identificadores,
  y elevar su rol a administrador.
- **Sitio de terceros:** intenta ejecutar mutaciones con la cookie de la víctima o leer respuestas
  desde otro origen.
- **Contenido subido:** un archivo o texto que llega al servidor para ser interpretado, incluido
  todo lo que se procese con OCR o se envíe a un modelo.
- **Cadena de suministro:** una dependencia con vulnerabilidad conocida o un secreto filtrado.

Quedan fuera: atacante con acceso físico al volumen, adversario con capacidad de romper Argon2id o
TLS, y amenazas internas del proveedor de despliegue.

## Principios

- **Confianza cero en la entrada:** todo lo que cruza el límite HTTP es hostil hasta validarse por
  esquema, tipo, tamaño y pertenencia.
- **Defensa en capas:** ningún control es la única barrera; si uno falla, otro limita el daño.
- **Falla cerrada:** ante duda, ambigüedad o error inesperado, deniega y registra.
- **Privilegio mínimo real:** cada actor recibe exactamente la capacidad que su tarea exige.
- **Costo acotado:** toda operación que un anónimo puede iniciar tiene techo de tamaño, frecuencia y
  tiempo.
- **Silencio hacia afuera, detalle hacia adentro:** el cliente recibe un mensaje genérico y el
  registro conserva la causa sin datos sensibles.
- **Proporcionalidad:** se añade un control cuando cierra una amenaza del modelo, no porque exista
  en una lista.

## Reglas obligatorias

### Identidad y sesión

- Deriva el propietario siempre de la sesión; ningún contrato de dominio acepta `user_id`.
- Persiste solo el digest del token de sesión, nunca el token.
- Rota la sesión al cambiar contraseña y revócala al desactivar la cuenta o restablecer credencial.
- Responde `404` ante un recurso ajeno; nunca `403`, que confirmaría su existencia.
- Usa el mismo mensaje y el mismo costo de verificación para usuario ausente y contraseña inválida.
- Marca la cookie `HttpOnly`, `SameSite=Strict`, `Path=/` y `Secure` en producción.

### Límites y disponibilidad

- Nunca uses una IP declarada por el cliente como identidad de confianza; deriva la IP del número
  exacto de proxies del despliegue.
- Un limitador debe acotar además la cuenta objetivo, para que rotar IP no restablezca el intento.
- Toda estructura en memoria alimentada por entrada anónima necesita cota y desalojo.
- Toda petición tiene tamaño máximo de cuerpo verificado antes de leerlo completo.

### Navegador

- Sirve `Content-Security-Policy` restrictiva sin `unsafe-inline` ni `unsafe-eval`.
- Mantén `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'none'` y `form-action 'self'`.
- Declara métodos y cabeceras permitidas explícitamente en CORS; no uses comodín con credenciales.
- Nunca construyas HTML con datos del usuario, del OCR o del modelo; usa el renderizado de React.

### Datos y registro

- No registres contraseñas, tokens, cookies, hashes, importes, descripciones, notas ni contenido de
  archivos.
- No pongas datos personales ni secretos en mensajes de error devueltos al cliente.
- Parametriza únicamente lo que cambia por entorno y documenta su valor local seguro.
- Un secreto vive en variables de entorno del proveedor, jamás en el repositorio ni en el cliente.

### Cadena de suministro

- Fija dependencias con lockfile e instala con instalación reproducible.
- Mantén el escaneo de dependencias y de secretos en integración continua.
- Concede a la integración continua el permiso mínimo.

## Flujo de trabajo

1. Nombra la amenaza concreta que el cambio cierra y el actor que la ejecuta.
2. Localiza el límite de confianza que atraviesa el dato: HTTP, configuración, persistencia,
   archivo o modelo.
3. Elige el control más simple que cierre la amenaza en ese límite.
4. Decide el comportamiento de falla: código, mensaje genérico y evento registrado.
5. Comprueba que el control no dependa de un valor controlado por el cliente.
6. Escribe la prueba del abuso, no solo la del camino feliz.
7. Verifica que el mensaje visible no revele existencia, estado interno ni datos ajenos.
8. Confirma que no se introdujeron secretos, registros sensibles ni parámetros sin propósito.

## Revisión de un cambio

Pregunta en este orden:

- ¿Qué puede enviar un anónimo a esta ruta y cuánto le cuesta repetirlo?
- ¿Qué pasa si el identificador pertenece a otra persona?
- ¿Qué pasa si el campo llega ausente, nulo, vacío, enorme o con el tipo equivocado?
- ¿Qué crece en memoria o en disco sin límite?
- ¿Qué se registra y quién podría leerlo?
- ¿Qué valor de la petición se está tratando como confiable sin serlo?
- ¿Qué ocurre si el proceso falla a mitad de la mutación?

## Verificación

- Prueba acceso sin sesión, con sesión expirada, con cuenta desactivada y con contraseña pendiente.
- Prueba lectura, edición y borrado de un identificador ajeno conocido.
- Prueba mutación sin `Origin` y con `Origin` de otro sitio.
- Prueba que rotar la IP declarada no restablece el bloqueo de intentos.
- Prueba que un cuerpo mayor al máximo se rechaza sin consumir el resto.
- Prueba que las cabeceras de seguridad aparecen también en respuestas de error.
- Prueba que la cookie es `Secure` en producción y no en desarrollo.
- Revisa que ningún registro nuevo contenga credenciales ni datos de dominio.
