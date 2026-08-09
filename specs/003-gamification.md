# 003 — Gamificación privada

## Estado

Primera versión implementada. Este contrato documenta la progresión existente y define cómo se
presenta el reconocimiento sin presión, comparación ni pérdida punitiva.

## Objetivos

- Reconocer acciones elegidas mediante XP, niveles e insignias comprensibles.
- Permitir un desafío semanal opcional y una recompensa personal definida por el usuario.
- Conservar la continuidad de una racha diaria mediante una recuperación limitada y transparente.
- Ofrecer retroalimentación visual inmediata, breve y accesible después de un éxito confirmado.
- Mantener la gamificación privada y secundaria frente a hábitos y finanzas.

## No objetivos

- Clasificaciones, perfiles sociales, rivales, avatares o actividad compartida.
- Recompensas aleatorias, cajas sorpresa, multiplicadores, apuestas o escasez artificial.
- Penalizaciones, pérdida de XP, degradación de nivel o mensajes de fracaso.
- Diagnosticar una conducta, afirmar que un hábito está formado o medir bienestar.
- Premiar montos, saldos, ahorro, gasto o cantidad de movimientos financieros.
- Sonido, vibración, notificaciones o movimiento decorativo continuo.

## Modelo

### XpEntry

Entrada inmutable del ledger. `source_type` y `source_id` forman una fuente lógica única.

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `amount` | integer | Positivo al reconocer; negativo al canjear |
| `source_type` | enum | Tipo estable del evento origen |
| `source_id` | string | Identificador mínimo, sin nombres, notas ni importes |
| `occurred_on` | date | Fecha civil del evento |
| `created_at` | datetime | UTC, solo lectura |

Catálogo de XP:

| Evento | XP |
| --- | ---: |
| Check-in ordinario de hábito | 10 |
| Primer presupuesto configurado | 20 |
| Revisión financiera semanal | 15 |
| Desafío semanal completado | 40 |
| Canje de recompensa | `-cost_xp` |

Una recuperación de racha no crea XP, progreso de desafío ni insignias.

### Progress

| Campo | Regla |
| --- | --- |
| `lifetime_xp` | Suma histórica de entradas positivas |
| `available_xp` | Suma de todas las entradas, nunca menor que cero |
| `level` | `floor(lifetime_xp / 100) + 1` |
| `level_start_xp` | XP acumulado al inicio del nivel |
| `next_level_xp` | XP acumulado requerido para el nivel siguiente |

Un canje reduce `available_xp`, pero nunca `lifetime_xp` ni el nivel.

### Badge

El catálogo es estable y cada insignia se concede como máximo una vez:

| Código | Criterio |
| --- | --- |
| `first_step` | Primer check-in de hábito |
| `steady_seven` | Siete check-ins acumulados |
| `challenge_complete` | Primer desafío semanal completado |
| `budget_ready` | Primer presupuesto configurado |
| `weekly_reviewed` | Primera revisión financiera semanal |
| `reward_claimed` | Primer canje de recompensa |

### WeeklyChallenge

| Campo | Tipo | Regla |
| --- | --- | --- |
| `week_start` | date | Lunes |
| `habit_id` | integer o null | Hábito activo o todos los hábitos |
| `target_count` | integer | Entre 1 y 7 |
| `progress_count` | integer | Check-ins aplicables de esa semana |
| `status` | enum | `active`, `completed` o `expired` |
| `completed_at` | datetime o null | UTC |

Solo existe un desafío por semana. Expirar no resta XP ni elimina el progreso visible.

### Reward y RewardRedemption

Una recompensa es una elección privada con `name`, `description` opcional, `cost_xp` positivo y
estado `active | archived`. El canje conserva el costo histórico y una `idempotency_key` única.
Solo se canjea una recompensa activa cuando hay XP disponible suficiente.

### StreakRecovery

| Campo | Tipo | Regla |
| --- | --- | --- |
| `habit_id` | integer | Hábito diario activo |
| `recovered_date` | date | Ayer o anteayer |
| `recovery_month` | string | `YYYY-MM`, una por hábito y mes |

La recuperación conserva continuidad en el cálculo de racha, pero no crea un check-in ni altera el
historial visible de cumplimiento.

### FinanceWeeklyReview

Confirma idempotentemente una revisión para un lunes no futuro. No copia importes, categorías,
saldos ni cantidad de movimientos.

## API

- `GET /api/v1/gamification/progress`
- `GET /api/v1/gamification/xp-entries`
- `GET /api/v1/gamification/badges`
- `GET /api/v1/gamification/weekly-challenges?week_start={monday}`
- `POST /api/v1/gamification/weekly-challenges`
- `DELETE /api/v1/gamification/weekly-challenges/{challenge_id}`
- `GET /api/v1/gamification/rewards?status={active|archived}`
- `POST /api/v1/gamification/rewards`
- `PATCH /api/v1/gamification/rewards/{reward_id}`
- `DELETE /api/v1/gamification/rewards/{reward_id}`
- `POST /api/v1/gamification/reward-redemptions`
- `GET /api/v1/gamification/reward-redemptions`
- `POST /api/v1/habits/{habit_id}/streak-recoveries`
- `PUT /api/v1/gamification/finance-reviews/{week_start}`

Repetir un check-in o una revisión no duplica reconocimiento. Repetir un canje con la misma clave
devuelve el canje existente. Recursos ausentes responden `404`, estados incompatibles `409` y
fechas o entradas inválidas `422`.

## Estados de interfaz

- **Carga:** superficie estable para progreso, desafío, insignias y recompensas.
- **Vacío:** explica cómo crear una recompensa o desafío sin presentarlos como obligación.
- **Progreso:** nivel, XP acumulado y disponible con texto además de representación gráfica.
- **Logro:** confirmación breve después de una respuesta exitosa; no se anticipa al servidor.
- **Insuficiente:** “XP insuficiente” deshabilita solo el canje afectado y no juzga.
- **Expirado:** “La semana terminó”; conserva el progreso y no usa color destructivo.
- **Recuperado:** confirma continuidad restaurada sin dibujar un check-in inexistente.
- **Error:** conserva datos previos, explica qué acción no se completó y permite continuar.
- **Movimiento reducido:** sustituye desplazamiento, escala y partículas por borde, color y texto.

## Retroalimentación visual

- Un check-in exitoso usa una microcelebración local y no abre modal ni mueve el foco.
- Nivel, insignia, desafío y canje pueden usar una celebración de hito descartable.
- Las celebraciones parten de contenido real de la acción; no inventan premios ni resultados.
- Desmarcar, archivar, eliminar o expirar no activa celebración.
- El detalle de movimiento, color y ornamentación se define en `specs/design-system.md`.

## Criterios de aceptación

- Procesar dos veces la misma fuente crea una sola entrada de XP y un solo efecto.
- El nivel depende de XP positivo de por vida; canjear no lo reduce.
- Un canje repetido o concurrente no cobra dos veces ni deja saldo negativo.
- Un desafío completado entrega XP una vez; uno expirado no penaliza.
- Una recuperación elegible afecta solo la racha y queda registrada una vez.
- Los eventos financieros permitidos no incluyen montos, saldos ni cantidad de movimientos.
- La función principal sigue disponible aunque el usuario ignore gamificación.
- El UI explica progreso con texto, funciona con teclado y no depende del color.
- Toda celebración ocurre después del éxito, puede descartarse, no atrapa foco y tiene alternativa
  estática con `prefers-reduced-motion`.
- Ningún texto usa culpa, comparación, amenaza de pérdida ni una afirmación clínica o conductual.

## Decisiones registradas

- **D-003-01:** usar un ledger idempotente como única fuente de XP.
- **D-003-02:** calcular nivel con XP positivo de por vida y saldo disponible con el ledger completo.
- **D-003-03:** mantener un catálogo pequeño y estable de insignias.
- **D-003-04:** permitir un desafío opcional por semana, sin penalización al expirar.
- **D-003-05:** hacer que el usuario defina sus recompensas y cobrar su costo de forma atómica.
- **D-003-06:** limitar la recuperación a una por hábito diario y mes, sin reconocerla como check-in.
- **D-003-07:** limitar reconocimiento financiero al primer presupuesto y la revisión semanal.
- **D-003-08:** separar el hecho de dominio de su celebración; solo una respuesta exitosa dispara
  feedback visual.
- **D-003-09:** tratar XP, rachas y engagement como contexto de interacción, no como prueba de cambio
  conductual.
# 003 — Gamificación privada

## Estado

Primera versión implementable. Define una capa opcional de progreso sobre hábitos y finanzas sin
comparación social, presión ni recompensas económicas.

## Contexto

La gamificación debe hacer visible el avance elegido por el usuario sin convertir una racha, un
saldo o una interacción frecuente en una medida de valor personal. Sigue autonomía, competencia y
privacidad: las acciones principales funcionan aunque el usuario ignore `/progreso`.

## Objetivos

- Registrar XP en un ledger auditable e idempotente.
- Calcular niveles y otorgar insignias con reglas explícitas.
- Permitir un desafío semanal privado y elegido por el usuario.
- Permitir recompensas personales y registrar sus canjes.
- Recuperar de forma limitada una racha diaria interrumpida.
- Reconocer en finanzas solo la configuración de un presupuesto y la revisión semanal.
- Mostrar celebraciones breves, descartables y reducibles.

## No objetivos

- Clasificaciones, perfiles públicos, competencia, comparación o funciones sociales.
- Moneda comprable, azar, cajas sorpresa, premios patrocinados o valor monetario real.
- Penalizar XP, nivel o insignias por ausencias, gastos, recaídas o rachas interrumpidas.
- Generar XP por montos, saldos, ahorro, cantidad de movimientos o frecuencia de apertura.
- Notificaciones, recordatorios, recomendaciones conductuales o personalización algorítmica.
- Convertir engagement, tiempo en pantalla o actividad en una medida de eficacia.

## Privacidad y tono

- Todos los recursos pertenecen al usuario implícito y no tienen rutas públicas ni campos sociales.
- El ledger guarda referencias técnicas a eventos, no nombres de hábitos, notas ni importes.
- Los textos describen hechos: “Nivel 3 alcanzado” o “Puedes recuperar ayer”; nunca “Fallaste”,
  “Sé responsable” ni equivalentes.
- Desactivar visualmente la gamificación no borra datos de hábitos o finanzas. La preferencia de
  visibilidad se diferirá hasta que existan ajustes globales.

## Modelo

### XpEntry

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `amount` | integer | Distinto de cero; negativo solo para un canje |
| `source_type` | enum | Evento admitido por la tabla de XP |
| `source_id` | string | Identidad estable del evento origen |
| `occurred_on` | date | Fecha civil del evento |
| `created_at` | datetime | UTC, solo lectura |

La combinación `source_type + source_id` es única. Procesar otra vez el mismo evento devuelve la
entrada existente y no cambia los totales.

| `source_type` | XP | `source_id` |
| --- | --- | --- |
| `habit_check_in` | 10 | Clave estable `{habit_id}:{check_in_date}` |
| `weekly_challenge` | 40 | ID de `WeeklyChallenge` completado |
| `finance_budget_setup` | 20 | Clave estable `initial` para el primer presupuesto |
| `finance_weekly_review` | 15 | ID de `FinanceWeeklyReview` |
| `reward_redemption` | `-Reward.cost_xp` | ID de `RewardRedemption` |

Eliminar un check-in no elimina XP ya reconocido. Volver a crearlo para el mismo hábito y fecha
reutiliza la misma clave y no genera XP otra vez. El ledger representa reconocimientos históricos,
no una proyección exacta del estado actual.

### Progress

No es una entidad persistente. Se calcula así:

- `lifetime_xp`: suma de entradas positivas.
- `available_xp`: suma de todas las entradas; nunca puede ser negativa.
- `level`: `floor(lifetime_xp / 100) + 1`.
- `level_start_xp`: `(level - 1) * 100`.
- `next_level_xp`: `level * 100`.

Los canjes reducen `available_xp`, pero nunca el nivel ni `lifetime_xp`.

### BadgeAward

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `badge_code` | enum | Código único por usuario |
| `awarded_at` | datetime | UTC, solo lectura |

Catálogo inicial:

| `badge_code` | Nombre visible | Regla |
| --- | --- | --- |
| `first_step` | Primer paso | Primer check-in de hábito |
| `steady_seven` | Siete avances | Siete check-ins acumulados |
| `challenge_complete` | Desafío cumplido | Primer desafío semanal completado |
| `budget_ready` | Presupuesto listo | Primer presupuesto configurado |
| `weekly_reviewed` | Semana revisada | Primera revisión financiera semanal |
| `reward_claimed` | Recompensa elegida | Primer canje de recompensa |

Otorgar una insignia es idempotente por `badge_code`. No se revoca si el evento de origen se elimina.

### WeeklyChallenge

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `week_start` | date | Lunes de la semana |
| `habit_id` | integer o null | Hábito activo; `null` incluye todos |
| `target_count` | integer | Entre 1 y 7 |
| `status` | enum | `active`, `completed` o `expired` |
| `completed_at` | datetime o null | UTC; se fija una vez |
| `created_at` | datetime | UTC, solo lectura |

Solo existe un desafío por `week_start`. Su progreso cuenta check-ins ordinarios de esa semana,
filtrados por `habit_id` cuando exista. Una recuperación no cuenta. Al alcanzar `target_count`, el
estado pasa una sola vez a `completed`; al terminar la semana sin alcanzarlo pasa a `expired` sin
penalización. `status` es una proyección de solo lectura: `completed` si existe `completed_at`,
`expired` si la semana terminó y `active` en otro caso. No requiere una tarea programada.

### Reward

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `name` | string | 1 a 80 caracteres |
| `description` | string o null | Máximo 240 caracteres |
| `cost_xp` | integer | Entre 1 y 10 000 |
| `status` | enum | `active` o `archived` |
| `created_at` | datetime | UTC, solo lectura |
| `updated_at` | datetime | UTC, solo lectura |

Una recompensa es una intención privada definida por el usuario. El sistema no afirma que tenga
valor económico ni verifica que se haya consumido fuera de la aplicación.

### RewardRedemption

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `reward_id` | integer | Recompensa activa |
| `cost_xp` | integer | Copia inmutable del costo al canjear |
| `idempotency_key` | string | UUID aportado por el cliente, único |
| `redeemed_at` | datetime | UTC, solo lectura |

El canje se crea en la misma transacción que su entrada negativa de XP. XP insuficiente responde
`409`; repetir la misma `idempotency_key` devuelve el canje existente.

### StreakRecovery

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `habit_id` | integer | Hábito diario activo |
| `recovered_date` | date | Fecha ausente recuperada |
| `recovery_month` | string | `YYYY-MM` derivado, persistido solo para unicidad |
| `created_at` | datetime | UTC, solo lectura |

`habit_id + recovered_date` y `habit_id + recovery_month` son únicos en la base de datos.
`recovery_month` no se expone en la API. Se permite una recuperación por hábito y mes civil de
`recovered_date`, para una de las dos fechas anteriores a hoy, si no existe check-in. Cuenta
únicamente para continuidad de racha: no crea `HabitCheckIn`, XP, progreso de desafío ni insignia.
No puede eliminarse. Dos solicitudes concurrentes para fechas distintas del mismo mes producen una
creación y un conflicto `409`.

### FinanceWeeklyReview

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `week_start` | date | Lunes, único por usuario |
| `created_at` | datetime | UTC, solo lectura |

Confirma que el usuario abrió el resumen y eligió “Marcar revisión completa”. No guarda montos,
categorías ni conteos.

## API

Todas las rutas usan `/api/v1`, el contrato común de errores y el usuario implícito.

### Progreso y ledger

- `GET /gamification/progress` devuelve `lifetime_xp`, `available_xp`, `level`,
  `level_start_xp` y `next_level_xp`.
- `GET /gamification/xp-entries` devuelve el ledger en orden descendente de `created_at`.
- No existe escritura pública de XP; los servicios de dominio procesan los eventos admitidos.

### Insignias

- `GET /gamification/badges` devuelve todo el catálogo con `code`, `name`, `description`,
  `awarded` y `awarded_at`.
- No existe endpoint para otorgar o revocar insignias manualmente.

### Desafíos

- `GET /gamification/weekly-challenges?week_start={monday}` devuelve el desafío de la semana o
  `404`.
- `POST /gamification/weekly-challenges` acepta `week_start`, `habit_id` y `target_count`; devuelve
  `201`, `422` para fecha o meta inválida y `409` si la semana ya tiene desafío.
- `DELETE /gamification/weekly-challenges/{challenge_id}` devuelve `204` solo mientras está
  `active`; un desafío completado o expirado responde `409`.

### Recompensas

- `GET /gamification/rewards?status=active` lista recompensas; `status=archived` lista archivadas.
- `POST /gamification/rewards` acepta `name`, `description` y `cost_xp`; devuelve `201`.
- `PATCH /gamification/rewards/{reward_id}` acepta esos campos enviados.
- `DELETE /gamification/rewards/{reward_id}` archiva y devuelve `204`.
- `POST /gamification/reward-redemptions` acepta `reward_id` e `idempotency_key`; devuelve `201`,
  o `200` al repetir la clave.
- `GET /gamification/reward-redemptions` lista canjes en orden descendente de `redeemed_at`.

### Recuperación y revisión financiera

- `POST /habits/{habit_id}/streak-recoveries` acepta `recovered_date`; devuelve `201`, `422` si la
  fecha no es elegible y `409` si ya se usó la recuperación mensual.
- `PUT /gamification/finance-reviews/{week_start}` crea la revisión y su XP o devuelve la existente
  con `200`; `week_start` debe ser lunes y no puede ser futuro.

## Estados de UI

- **Oculto en contexto:** hábitos y finanzas funcionan sin mostrar XP durante la captura.
- **Carga:** estructura estable de nivel, insignias, desafío y recompensas.
- **Vacío:** explica una sola función y ofrece crear un desafío o recompensa, sin urgencia.
- **Progreso:** nivel y XP se muestran como contexto secundario, con texto además de la barra.
- **Logro:** confirmación breve y descartable; con movimiento reducido es estática.
- **Desafío activo:** objetivo, progreso y semana visibles; sin cuenta regresiva.
- **Desafío expirado:** texto “La semana terminó” y acción para crear uno nuevo; sin pérdida visual.
- **Canje insuficiente:** muestra XP disponible y permite volver, sin sugerir más actividad.
- **Racha interrumpida:** ofrece recuperación solo si es elegible; siempre permite continuar hoy.
- **Error:** conserva los datos previos y ofrece reintentar la operación afectada.

## Criterios de aceptación

- Un evento procesado dos veces produce una sola entrada de XP y un solo efecto en los totales.
- Eliminar y volver a crear un check-in para el mismo hábito y fecha no duplica XP.
- El nivel depende solo de XP positivo acumulado y no baja al canjear.
- Ningún saldo, monto, ahorro, gasto o cantidad de movimientos genera XP o insignias.
- Configurar el primer presupuesto genera XP una sola vez; editarlo, eliminarlo o crear otros no
  genera XP adicional.
- Una revisión semanal genera XP una sola vez por lunes y no guarda datos financieros.
- Un desafío completado genera XP una sola vez; expirar o eliminar no resta XP.
- Un canje concurrente no puede dejar `available_xp` negativo y una clave repetida no cobra dos veces.
- Una recuperación elegible preserva la racha sin crear check-in, XP, desafío ni insignia.
- La base de datos impide dos recuperaciones concurrentes para el mismo hábito y mes.
- Insignias y ledger no contienen nombres, notas, importes ni datos públicos.
- Toda celebración es descartable, no bloquea el flujo y tiene alternativa sin movimiento.
- Ausencias, retos expirados y XP insuficiente usan lenguaje neutral y nunca vergüenza o presión.
- Los flujos son operables con teclado, foco visible y significado independiente del color.

## Decisiones registradas

- **D-003-01:** usar un ledger de XP inmutable con unicidad por evento para garantizar auditoría e
  idempotencia.
- **D-003-02:** separar `lifetime_xp` de `available_xp` para que los canjes no reduzcan el nivel.
- **D-003-03:** fijar niveles de 100 XP sin curva configurable hasta contar con evidencia de uso.
- **D-003-04:** mantener un catálogo pequeño de insignias con criterios verificables y privados.
- **D-003-05:** permitir un desafío elegido por semana y hacerlo expirar sin penalización.
- **D-003-06:** tratar recompensas como intenciones definidas por el usuario, sin valor monetario ni
  verificación externa.
- **D-003-07:** limitar la recuperación a hábitos diarios, una vez por mes y dentro de dos días,
  sin recompensarla con XP.
- **D-003-08:** premiar en finanzas solo crear un presupuesto y confirmar una revisión semanal.
- **D-003-09:** prohibir XP financiero basado en montos, saldos, ahorro o cantidad de movimientos.
- **D-003-10:** no exponer mutaciones directas del ledger ni de insignias.
- **D-003-11:** mantener toda la gamificación privada y sin telemetría, perfiles o comparaciones.
- **D-003-12:** usar celebraciones breves, descartables y estáticas con movimiento reducido.
- **D-003-13:** conservar el XP histórico al eliminar un check-in y usar hábito más fecha como clave
  para impedir que recrearlo duplique el reconocimiento.
- **D-003-14:** persistir el mes derivado de una recuperación y exigir unicidad por hábito y mes en
  la base de datos para que el límite sea atómico.
- **D-003-15:** al migrar datos inválidos con varias recuperaciones del mismo hábito y mes, conservar
  la de menor `id` y retirar las posteriores antes de crear la restricción.
