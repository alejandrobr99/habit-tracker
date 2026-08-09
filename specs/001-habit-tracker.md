# 001 — Seguimiento de hábitos

## Estado

Primera versión implementable. Este contrato elige cumplimiento binario y dos frecuencias para
evitar un motor de recurrencias prematuro.

## Objetivos

- Crear, editar y archivar hábitos.
- Registrar o deshacer un cumplimiento para una fecha.
- Distinguir hábitos para construir una conducta (`build`) y para evitarla (`avoid`).
- Consultar la semana visible y una racha comprensible.
- Mostrar en Hoy las acciones activas y su progreso.

## No objetivos

- Días personalizados, horarios, cantidades, notas por registro u omisiones.
- Reordenamiento, recordatorios, historial mensual o actualización optimista.
- Recomendaciones y correcciones masivas.
- Registrar recaídas, motivos, contenido sensible o compartir actividad.

La progresión, las insignias, los desafíos y la recuperación de rachas se definen en
`specs/003-gamification.md`; este contrato solo expone los hechos de hábitos que las originan.

## Modelo

### Habit

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `name` | string | 1 a 120 caracteres tras recortar espacios |
| `description` | string o null | Nota opcional |
| `direction` | enum | `build` o `avoid` |
| `frequency` | enum | `daily` o `weekly` |
| `status` | enum | `active` o `archived` |
| `color` | string | Color hexadecimal de seis dígitos |
| `created_at` | datetime | UTC, solo lectura |
| `updated_at` | datetime | UTC, solo lectura |

### HabitCheckIn

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `habit_id` | integer | Referencia a `Habit` |
| `check_in_date` | date | Único junto con `habit_id` |
| `created_at` | datetime | UTC, solo lectura |

La ausencia de un check-in significa pendiente. En `build`, el check-in confirma que se realizó la
conducta; en `avoid`, confirma que se evitó durante la fecha o periodo elegido. No se persisten
recaídas: el usuario puede volver a registrar el siguiente cumplimiento sin explicar una ausencia.
Archivar conserva los registros.

## Reglas de dominio

- Un check-in es idempotente: repetir el mismo `PUT` devuelve el registro existente.
- Un hábito archivado no acepta check-ins nuevos y responde `409`.
- Cambiar `direction` después del primer check-in responde `409`; nombre, descripción, frecuencia
  y color siguen siendo editables.
- La racha diaria cuenta fechas consecutivas; hoy puede estar pendiente sin romper la racha.
- La racha semanal cuenta semanas consecutivas con al menos un cumplimiento.
- La meta visible es siete para frecuencia diaria y uno para frecuencia semanal.
- La semana comienza el lunes y `week_start` debe ser lunes.

## API

- `GET /api/v1/habits`: lista hábitos activos.
- `GET /api/v1/habits?status=archived`: lista archivados.
- `POST /api/v1/habits`: crea un hábito; acepta `name`, `description`, `direction`, `frequency` y
  `color`.
- `PATCH /api/v1/habits/{habit_id}`: modifica cualquiera de esos campos enviado y aplica el
  conflicto de `direction`.
- `DELETE /api/v1/habits/{habit_id}`: archiva y devuelve el hábito.
- `PUT /api/v1/habits/{habit_id}/check-ins/{date}`: registra cumplimiento.
- `DELETE /api/v1/habits/{habit_id}/check-ins/{date}`: elimina cumplimiento.
- `GET /api/v1/habits/weekly-summary?week_start={monday}`: devuelve hábitos, fechas,
  cumplimiento, meta y racha.

## Estados de interfaz

- **Carga:** bloque estable con explicación breve.
- **Vacío:** una acción principal para crear el primer hábito.
- **Error:** mensaje local y acción para reintentar.
- **Guardando:** deshabilitar solo los controles que puedan duplicar la mutación.
- **Listo:** semana, acciones, progreso y racha visibles.
- **Archivado:** confirmación antes de retirar el hábito de las vistas activas.
- **Recuperado:** una fecha reparada se distingue con texto neutral y sin simular un check-in
  ordinario. Mientras el resumen semanal no exponga fechas recuperadas, la distinción aparece en
  la confirmación de la acción y en la continuidad de la racha, no dentro de una celda diaria.

## Criterios de aceptación

- Crear, editar y archivar persiste después de recargar.
- Nombre, dirección, frecuencia y color inválidos responden `422`.
- Un hábito y fecha nunca tienen más de un check-in.
- Registrar dos veces es seguro; eliminar dos veces termina en `404`.
- Un hábito archivado conserva historial y rechaza nuevos registros.
- Las rachas diarias y semanales respetan las reglas definidas.
- Los hábitos `avoid` usan “Evitado” y “Pendiente”, nunca lenguaje de culpa ni un registro de
  recaídas.
- La racha visible usa “días” para frecuencia `daily` y “semanas” para frecuencia `weekly`.
- La API no expone check-ins fuera del usuario implícito ni incorpora telemetría de hábitos.
- Hoy y Hábitos representan carga, vacío, error y contenido.
- Crear, editar, archivar y marcar son operables con teclado.

## Decisiones registradas

- **D-001-01:** modelar pendiente como ausencia de check-in.
- **D-001-02:** limitar recurrencia a `daily` y `weekly`.
- **D-001-03:** usar archivado lógico y cumplimiento binario.
- **D-001-04:** posponer programación por días, notas y omisiones hasta validar su necesidad.
- **D-001-05:** usar enteros locales como identidad mientras no exista sincronización.
- **D-001-06:** representar la intención con `direction: build | avoid` y mantener un único
  significado positivo del check-in: cumplimiento elegido por el usuario.
- **D-001-07:** no persistir recaídas ni explicaciones de ausencias para reducir datos sensibles y
  evitar una experiencia moralizante.
- **D-001-08:** impedir el cambio de dirección después del primer check-in para conservar el
  significado del historial.
- **D-001-09:** no representar visualmente una recuperación como check-in mientras el resumen
  semanal no exponga su fecha; la recuperación solo restaura continuidad.
