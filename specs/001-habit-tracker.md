# 001 — Seguimiento de hábitos

## Estado

Propuesta para la primera funcionalidad completa.

## Contexto

El seguimiento debe responder dos preguntas: qué corresponde hacer hoy y qué se ha sostenido en
el tiempo. Registrar una acción debe ser inmediato, reversible y libre de presión innecesaria.

## Objetivos

- Crear, editar, archivar y ordenar hábitos.
- Mostrar los hábitos activos correspondientes a una fecha.
- Registrar un hábito como completado, omitido o pendiente.
- Consultar un historial breve y una racha comprensible.
- Permitir notas cortas por registro sin convertirlas en diario.

## No objetivos

- Hábitos compartidos, retos, puntos, insignias o tablas de clasificación.
- Recordatorios, notificaciones push o integración con calendario.
- Frecuencias por hora, múltiples objetivos diarios o métricas cuantitativas.
- Análisis predictivo, recomendaciones automáticas o corrección retroactiva masiva.

## Modelo

### Habit

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | string | Opaco e inmutable |
| `name` | string | Entre 1 y 80 caracteres tras recortar espacios |
| `description` | string o null | Máximo 240 caracteres |
| `schedule_days` | entero[] | Días ISO, 1 lunes a 7 domingo; sin duplicados |
| `color` | string | Token semántico permitido, no color hexadecimal libre |
| `position` | entero | Orden ascendente entre hábitos activos |
| `archived_at` | datetime o null | Archivado lógico |
| `created_at` | datetime | Solo lectura |
| `updated_at` | datetime | Solo lectura |

### HabitEntry

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | string | Opaco e inmutable |
| `habit_id` | string | Referencia a `Habit` |
| `date` | date | Único junto con `habit_id` |
| `status` | enum | `completed`, `skipped` |
| `note` | string o null | Máximo 240 caracteres |
| `created_at` | datetime | Solo lectura |
| `updated_at` | datetime | Solo lectura |

La ausencia de `HabitEntry` significa `pending`. Una omisión es deliberada y no rompe una racha:
queda visible, pero no cuenta como cumplimiento. Un día fuera de `schedule_days` no participa.

## Reglas de dominio

- Un hábito debe tener al menos un día programado.
- Archivar conserva entradas e historial; el hábito deja de aparecer desde el día siguiente.
- La pantalla de una fecha pasada permite corregir entradas; una fecha futura es de solo lectura.
- La racha cuenta días programados completados consecutivamente hasta la fecha consultada.
- Los días omitidos se ignoran al calcular continuidad; un día pendiente pasado termina la racha.
- Cambiar la programación afecta cálculos desde el cambio en adelante. La primera versión no
  conserva versiones históricas de la programación y debe comunicar esta limitación.

## API

### Hábitos

- `GET /api/v1/habits?include_archived=false`: lista ordenada.
- `POST /api/v1/habits`: crea un hábito.
- `GET /api/v1/habits/{habit_id}`: devuelve detalle y resumen.
- `PATCH /api/v1/habits/{habit_id}`: modifica campos enviados.
- `DELETE /api/v1/habits/{habit_id}`: archiva; no elimina físicamente.
- `PUT /api/v1/habits/order`: recibe `{ "habit_ids": [...] }` con todos los activos.

### Registros y vista diaria

- `GET /api/v1/habits/daily?date=YYYY-MM-DD`: devuelve hábitos programados, estado y racha.
- `PUT /api/v1/habits/{habit_id}/entries/{date}`: crea o reemplaza estado y nota.
- `DELETE /api/v1/habits/{habit_id}/entries/{date}`: vuelve el día a pendiente.
- `GET /api/v1/habits/{habit_id}/entries?from=YYYY-MM-DD&to=YYYY-MM-DD`: devuelve historial.

El backend responde `409` si se registra un hábito archivado o no programado para esa fecha. El
orden inválido responde `422` sin aplicar cambios parciales.

## Flujo de interfaz

### Vista de hoy

1. El encabezado muestra fecha local y progreso `completados / programados`.
2. Cada fila presenta nombre, estado y una acción de completar de un solo toque.
3. Un menú secundario permite omitir, añadir nota o deshacer.
4. La actualización es optimista; ante error se revierte el estado y se conserva el foco.

### Gestión

1. “Nuevo hábito” abre un panel lateral o diálogo.
2. Nombre y días son obligatorios; la validación aparece al perder foco y al enviar.
3. Guardar cierra el panel, inserta el hábito en orden y lleva el foco al resultado.
4. Editar reutiliza el formulario; archivar requiere confirmación contextual.
5. Reordenar ofrece controles accesibles además de arrastrar.

### Detalle

Muestra nombre, racha actual, cumplimiento de las últimas cuatro semanas y registros recientes.
No usa un calendario denso como vista principal.

## Estados de UI

- **Carga:** filas esqueleto con el alto final.
- **Sin hábitos:** explicación breve y botón “Crear primer hábito”.
- **Día sin hábitos programados:** mensaje de descanso, sin llamada urgente a crear.
- **Error de lista:** mensaje en el área de contenido y “Reintentar”.
- **Mutación en curso:** control afectado bloqueado, resto de la lista operativo.
- **Conflicto:** revertir cambio, explicar la causa y ofrecer actualizar.
- **Archivado:** confirmación discreta con opción inmediata de deshacer mientras sea viable.
- **Historial vacío:** indicar que aparecerá tras el primer registro.

## Criterios de aceptación

- Se puede crear un hábito válido con nombre y al menos un día, y aparece en la fecha correcta.
- Nombre vacío, longitud excesiva y programación vacía muestran errores específicos.
- Completar, omitir y volver a pendiente persiste tras recargar.
- Dos registros para el mismo hábito y fecha nunca coexisten.
- Una acción optimista fallida restaura el estado anterior.
- Archivar retira el hábito de vistas futuras y conserva su historial.
- La racha respeta días programados, omitidos y pendientes según las reglas descritas.
- Crear, registrar, reordenar y archivar son operables con teclado.
- Los estados vacío, carga, error y día de descanso tienen representación explícita.

## Decisiones registradas

- **D-001-01:** modelar `pending` como ausencia de entrada para evitar datos redundantes.
- **D-001-02:** permitir `skipped` como pausa neutral que no aumenta ni rompe la racha.
- **D-001-03:** usar archivado lógico para preservar continuidad e historial.
- **D-001-04:** limitar la primera versión a cumplimiento binario por día.
- **D-001-05:** priorizar una lista diaria sobre un calendario mensual.

## Preguntas abiertas

- ¿Debe una corrección pasada recalcular y mostrar inmediatamente todas las rachas visibles?
- ¿Se necesita una fecha explícita de inicio para evitar días pendientes anteriores a la creación?
