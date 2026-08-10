# 003 — Gamificación privada

## Estado

Primera versión implementada. Este contrato documenta la progresión existente y define cómo se
presenta el reconocimiento sin presión, comparación ni pérdida punitiva.

## Objetivos

- Reconocer acciones elegidas mediante XP, niveles e insignias comprensibles.
- Permitir un desafío semanal opcional y una recompensa personal definida por el usuario.
- Conservar la continuidad de una racha diaria mediante una recuperación limitada y transparente.
- Ofrecer retroalimentación visual inmediata y accesible después de un éxito confirmado.
- Mantener la gamificación privada para la cuenta autenticada y secundaria frente a hábitos y
  finanzas.

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
- **Logro:** confirmación después de una respuesta exitosa; no se anticipa al servidor.
- **Insuficiente:** “XP insuficiente” deshabilita solo el canje afectado y no juzga.
- **Expirado:** “La semana terminó”; conserva el progreso y no usa color destructivo.
- **Recuperado:** confirma continuidad restaurada sin dibujar un check-in inexistente.
- **Error:** conserva datos previos, explica qué acción no se completó y permite continuar.
- **Movimiento reducido:** sustituye desplazamiento, escala y partículas por borde, color y texto.

## Retroalimentación visual

- Un check-in exitoso usa una microcelebración local y no abre modal ni mueve el foco.
- Nivel, insignia, desafío y canje pueden usar una celebración de hito descartable.
- Una racha usa celebración escénica al alcanzar 3, 7, 14 o 30 periodos y cada múltiplo posterior de
  30. La unidad es días para hábitos diarios y semanas para hábitos semanales.
- Completar la meta semanal de un hábito o todos los hábitos activos de hoy también permite una
  celebración escénica.
- Si un check-in alcanza varios hitos simultáneos, se muestra una sola escena con prioridad:
  día completo, meta semanal y racha.
- Las celebraciones parten de contenido real de la acción; no inventan premios ni resultados.
- Desmarcar, archivar, eliminar, recuperar o expirar no activa celebración escénica.
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
- Una celebración escénica se activa una vez por mutación confirmada y desaparece sin exigir acción.
- Ningún texto usa culpa, comparación, amenaza de pérdida ni una afirmación clínica o conductual.
- XP, insignias, desafíos, recompensas y revisiones se calculan solo con datos de su propietario.

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
- **D-003-10:** reservar la celebración escénica para día completo, meta semanal y rachas de 3, 7,
  14, 30 o múltiplos de 30, priorizando una sola escena cuando coincidan.
