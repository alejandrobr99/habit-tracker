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
