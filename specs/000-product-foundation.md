# 000 — Fundamentos del producto

## Estado

Propuesta inicial. Este documento define el contrato común para las primeras entregas.

## Contexto

El producto es un planificador personal privado para convertir intenciones cotidianas en
acciones visibles. Debe reunir hábitos y finanzas sin convertirse en una plataforma de
productividad genérica ni en un sistema contable.

## Objetivos

- Ofrecer una vista diaria serena, legible y útil en menos de un minuto.
- Mantener hábitos y finanzas como dominios separados dentro de una experiencia coherente.
- Priorizar captura rápida, estados explícitos y retroalimentación sobria.
- Hacer visible el progreso mediante gamificación opcional, privada y no moralizante.
- Diseñar contratos que permitan evolucionar backend y frontend de forma independiente.
- Hacer de las especificaciones la fuente de verdad antes de implementar.

## No objetivos

- Colaboración, cuentas familiares o espacios compartidos.
- Comparaciones sociales, clasificaciones públicas o recompensas con valor monetario real.
- Sincronización bancaria, asesoría financiera o contabilidad fiscal.
- Calendario completo, gestión de proyectos o automatizaciones externas en la primera etapa.
- Aplicaciones móviles nativas y funcionamiento sin conexión.

## Principios del producto

1. **Calma antes que densidad:** mostrar solo la información necesaria para la decisión actual.
2. **Control del usuario:** ninguna acción destructiva o financiera se ejecuta implícitamente.
3. **Progreso honesto:** evitar métricas que castiguen descansos o exageren resultados.
4. **Accesibilidad por defecto:** teclado, foco visible, contraste AA y texto comprensible.
5. **Privacidad local:** minimizar datos personales y no incorporar telemetría sin una decisión.
6. **Sencillez deliberada:** elegir código directo y robusto antes que abstracciones o
   infraestructura anticipada.
7. **Motivación sin presión:** puntos, niveles, insignias, desafíos, recompensas personales y
   recuperación de rachas reconocen acciones elegidas; nunca califican el carácter ni usan culpa,
   urgencia artificial o pérdida como castigo.

La gamificación se define en `specs/003-gamification.md`. Es privada para el usuario implícito,
puede ignorarse sin bloquear hábitos o finanzas y usa celebraciones breves que se reducen o
eliminan con la preferencia de movimiento reducido.

La toma de decisiones técnicas se rige por `specs/constitution.md`. En particular, solo se
parametrizan valores que varían por entorno o instalación; las reglas de producto permanecen como
código versionado.

## Arquitectura prevista

Monorepo con tres áreas:

- `specs/`: contratos funcionales, visuales y decisiones.
- `backend/`: API HTTP en Python 3.11, gestionada con `uv`.
- `frontend/`: cliente web TypeScript, gestionado con `npm`.

La API usa JSON, rutas versionadas bajo `/api/v1` y fechas civiles en formato `YYYY-MM-DD`.
Los instantes se intercambian en ISO 8601 con zona horaria. El almacenamiento inicial puede ser
SQLite, sin acoplar el contrato HTTP al motor elegido.

## Modelo de dominio común

### Identidad y tiempo

- Todos los recursos persistidos tienen `id` estable y `created_at`; los recursos mutables también
  tienen `updated_at`.
- El único usuario inicial es implícito; no se expone autenticación hasta especificarla.
- `date` representa el día local elegido por el usuario.
- El backend conserva instantes en UTC y el frontend presenta la zona configurada.

### Convenciones

- Los importes monetarios se expresan en unidades menores enteras y llevan código ISO 4217.
- Los campos opcionales usan `null`; un campo ausente no equivale a borrar su valor.
- Las colecciones pequeñas se devuelven como arreglos JSON. Se añade un sobre con metadatos solo
  cuando una necesidad real de paginación lo requiera.
- Los errores usan inicialmente el campo estándar `detail` de FastAPI. Un contrato de error propio
  se añadirá cuando el cliente necesite distinguir errores por código estable.

## Contrato API común

- Base: `/api/v1`.
- `GET /health`: confirma disponibilidad sin revelar datos internos.
- Respuestas exitosas de creación: `201`.
- Validación: `422`; recurso inexistente: `404`; conflicto de estado: `409`.
- Borrado exitoso sin cuerpo: `204`.
- La paginación y autenticación quedan diferidas hasta que el volumen o despliegue las exijan.

## Estructura de navegación

- `/`: hoy, con resumen de hábitos y acceso directo a finanzas.
- `/habitos`: gestión e historial de hábitos.
- `/finanzas`: movimientos, presupuestos y resumen mensual.
- `/progreso`: nivel, insignias, desafíos y recompensas personales.
- Ajustes globales solo se añaden cuando exista una necesidad definida.

## Estados globales de interfaz

- **Cargando:** esqueleto estable; no usar indicadores que desplacen contenido.
- **Vacío:** explicar el beneficio y ofrecer una única acción primaria.
- **Listo:** contenido, acción principal y contexto temporal visibles.
- **Error recuperable:** mensaje cercano al contenido y acción para reintentar.
- **Sin conexión:** conservar la pantalla y explicar que no se guardarán cambios.
- **Guardando:** deshabilitar solo el control afectado y prevenir envíos duplicados.
- **Éxito:** reflejar el resultado en la interfaz; evitar notificaciones redundantes.
- **Celebración:** reconocimiento breve y descartable; no bloquea la siguiente acción y se
  convierte en confirmación estática con `prefers-reduced-motion`.

## Criterios de aceptación

- Existe una ruta clara desde la vista de hoy hacia hábitos y finanzas.
- Cada pantalla implementada contempla carga, vacío, error y contenido.
- La interfaz es operable con teclado y conserva foco visible.
- Los contratos de cada dominio respetan las convenciones de identidad, tiempo, errores y dinero.
- La gamificación no publica actividad, no exige participación y no usa montos financieros ni
  cantidad de movimientos como señal de mérito.
- Ninguna funcionalidad fuera de alcance aparece como activa; las funciones futuras se etiquetan
  como no disponibles o se omiten.
- Una modificación funcional comienza actualizando o creando una especificación numerada.

## Decisiones registradas

- **D-000-01:** comenzar con un solo usuario implícito para validar el flujo principal.
- **D-000-02:** separar contratos de producto de detalles de persistencia.
- **D-000-03:** usar rutas API versionadas desde el inicio.
- **D-000-04:** adoptar una estética cálida y neutral, definida en `design-system.md`.
- **D-000-05:** tratar hábitos y finanzas como módulos independientes con navegación compartida.
- **D-000-06:** adoptar `specs/constitution.md` como criterio para simplicidad, parametrización,
  pruebas y optimización.
- **D-000-07:** evitar sobres de colección y errores personalizados hasta que exista una necesidad
  concreta del cliente.
- **D-000-08:** ofrecer gamificación privada y opcional como capa de retroalimentación, sin
  comparaciones sociales ni bloqueos sobre las funciones principales.
- **D-000-09:** limitar la gamificación financiera a configurar un presupuesto y completar una
  revisión semanal, sin premiar montos, saldos ni cantidad de movimientos.
- **D-000-10:** exigir `updated_at` solo en recursos mutables y conservar eventos inmutables con
  `created_at`.

## Preguntas abiertas

- ¿La zona horaria será una preferencia persistida o se derivará siempre del navegador?
- ¿Qué mecanismo de autenticación será adecuado cuando el producto deje de ser local?
- ¿Cuándo el volumen real justificará paginación y una base de datos distinta de SQLite?
