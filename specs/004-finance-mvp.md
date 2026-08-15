# 004 — Finanzas MVP

## Estado

Primera versión implementable. Sustituye el shell demostrativo de `specs/002-finance-shell.md` por
captura manual y resumen real, sin modelar cuentas ni integraciones.

## Contexto

El primer incremento financiero permite responder cuánto ingresó, cuánto se gastó y cómo avanza el
presupuesto del mes. Los datos permanecen privados en la instalación local y la interfaz evita
juicios sobre montos o decisiones de consumo.

## Objetivos

- Configurar una única moneda base.
- Crear, editar y archivar categorías personales.
- Registrar, editar, listar y eliminar movimientos manuales `income` o `expense`.
- Definir presupuestos mensuales por categoría de gasto.
- Consultar un resumen mensual derivado de movimientos y presupuestos.
- Priorizar captura rápida, importes exactos y lenguaje neutral.

## No objetivos

- Cuentas, saldos por cuenta, transferencias o conciliación.
- Sincronización bancaria, importación de archivos o movimientos recurrentes.
- Monedas múltiples, conversión, tasas de cambio o cambio de moneda con datos existentes.
- Deudas, inversiones, impuestos, patrimonio, proyecciones o asesoría financiera.
- Adjuntos permanentes, comercios, etiquetas, división de movimientos o reglas automáticas. La
  importación temporal de documentos y su confirmación humana se especifica en
  `specs/007-finance-document-import.md`.
- Compartir datos, telemetría financiera o gamificación basada en montos o cantidad de movimientos.

## Convenciones

- Todos los importes son enteros positivos en unidades menores; la dirección está en `type`.
- La API nunca acepta números decimales, flotantes, símbolos ni cadenas formateadas como importe.
- La moneda usa un código alfabético ISO 4217 activo y su exponente de unidades menores.
- `month` usa `YYYY-MM`; `date` usa `YYYY-MM-DD`; los instantes siguen el contrato común.
- El resumen se deriva al consultar y no se persiste como saldo.
- Las listas son pequeñas, sin paginación en este alcance.

## Modelo

### FinanceSettings

Recurso singleton con identidad estable `id = 1`.

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Siempre `1` |
| `base_currency` | string | Código ISO 4217 alfabético activo |
| `minor_unit` | integer | Exponente ISO 4217, solo lectura |
| `created_at` | datetime | UTC, solo lectura |
| `updated_at` | datetime | UTC, solo lectura |

La moneda puede configurarse por primera vez o cambiarse mientras no existan movimientos ni
presupuestos. Después, un cambio responde `409`; enviar la moneda actual sigue siendo idempotente.

### Category

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `name` | string | 1 a 60 caracteres tras recortar espacios |
| `type` | enum | `income` o `expense` |
| `color` | string | Hexadecimal de seis dígitos |
| `status` | enum | `active` o `archived` |
| `created_at` | datetime | UTC, solo lectura |
| `updated_at` | datetime | UTC, solo lectura |

`name + type` es único sin distinguir mayúsculas entre categorías activas. Archivar conserva
movimientos y presupuestos históricos. Una categoría con referencias no se elimina físicamente.
No se crean categorías predeterminadas.

### Transaction

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `type` | enum | `income` o `expense` |
| `amount_minor` | integer | Mayor que cero |
| `category_id` | integer | Categoría activa del mismo `type` al crear |
| `date` | date | Fecha civil |
| `description` | string | 1 a 120 caracteres |
| `note` | string o null | Máximo 500 caracteres |
| `created_at` | datetime | UTC, solo lectura |
| `updated_at` | datetime | UTC, solo lectura |

La moneda del movimiento es siempre `FinanceSettings.base_currency` y no se repite en cada fila.
Editar `type` exige una categoría activa compatible en la misma solicitud. Archivar una categoría
no modifica movimientos existentes.

### Budget

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base de datos |
| `month` | string | `YYYY-MM` válido |
| `category_id` | integer | Categoría `expense` activa al crear |
| `limit_minor` | integer | Mayor que cero |
| `created_at` | datetime | UTC, solo lectura |
| `updated_at` | datetime | UTC, solo lectura |

`month + category_id` es único. Un presupuesto compara el límite con la suma de gastos de esa
categoría cuya `date` pertenece al mes. Eliminarlo no elimina movimientos.

### MonthlySummary

No se persiste. La respuesta contiene:

| Campo | Tipo | Regla |
| --- | --- | --- |
| `month` | string | Periodo solicitado |
| `currency` | string | Moneda base |
| `income_minor` | integer | Suma de ingresos del mes |
| `expense_minor` | integer | Suma de gastos del mes |
| `balance_minor` | integer | `income_minor - expense_minor` |
| `budgeted_minor` | integer | Suma de límites del mes |
| `budget_remaining_minor` | integer | `budgeted_minor -` gasto de categorías presupuestadas |
| `categories` | array | Desglose de categorías con actividad o presupuesto |

Cada elemento de `categories` contiene `category_id`, `category_name`, `type`, `actual_minor`,
`budget_minor` y `remaining_minor`. `budget_minor` y `remaining_minor` son `null` para ingresos o
gastos sin presupuesto. Un `remaining_minor` negativo expresa que el límite fue superado sin usar
lenguaje de culpa.

## Reglas de dominio

- Configurar moneda es requisito para crear movimientos o presupuestos; su ausencia responde `409`.
- Una categoría archivada puede consultarse en históricos, pero no recibe movimientos o
  presupuestos nuevos.
- El backend valida el tipo de la categoría; no confía en el cliente.
- Los importes no llevan signo. `expense` resta e `income` suma únicamente al calcular el resumen.
- El resumen mensual incluye movimientos por su `date`, no por `created_at`.
- El cálculo presupuestario ignora ingresos y gastos de categorías sin presupuesto.
- Crear el primer presupuesto puede originar el reconocimiento definido en
  `specs/003-gamification.md`; montos, ediciones y movimientos nunca originan XP.
- Ninguna respuesta incluye agregados de otros usuarios ni datos de demostración.

## API

Todas las rutas usan `/api/v1`, JSON y el contrato común de errores.

### Moneda base

- `GET /finance/settings` devuelve el singleton o `404` si aún no se configuró.
- `PUT /finance/settings` acepta exactamente `{"base_currency": "COP"}`. Devuelve `201` al crear,
  `200` al repetir o cambiar antes de tener datos, `422` para código inválido y `409` al intentar
  cambiarlo con movimientos o presupuestos existentes.

La respuesta es `FinanceSettings`. `minor_unit` se obtiene del catálogo ISO 4217 del backend.

### Categorías

- `GET /finance/categories?status=active` lista activas ordenadas por `type`, `name`; acepta
  `status=archived`.
- `POST /finance/categories` acepta `name`, `type` y `color`; devuelve `201`.
- `PATCH /finance/categories/{category_id}` acepta uno o más de `name`, `type`, `color`.
- `DELETE /finance/categories/{category_id}` archiva y devuelve `204`.

Cambiar `type` con movimientos o presupuestos asociados responde `409`. Nombre duplicado responde
`409`; valores inválidos responden `422`; categoría inexistente responde `404`.

### Movimientos

- `GET /finance/transactions?month={YYYY-MM}` lista el mes por `date` descendente y luego `id`
  descendente.
- `GET /finance/transactions/range?start_month={YYYY-MM}&end_month={YYYY-MM}` lista el rango
  inclusivo por `date` descendente y luego `id` descendente.
- `GET /finance/transactions/export-selected?months={YYYY-MM}&months={YYYY-MM}` descarga los meses
  seleccionados en `.xlsx`, sin notas.
- `POST /finance/transactions` acepta `type`, `amount_minor`, `category_id`, `date`,
  `description` y `note`; devuelve `201`.
- `GET /finance/transactions/{transaction_id}` devuelve un movimiento.
- `PATCH /finance/transactions/{transaction_id}` acepta uno o más campos mutables del cuerpo de
  creación y devuelve el movimiento actualizado.
- `DELETE /finance/transactions/{transaction_id}` elimina y devuelve `204`.

`month` o campos inválidos responden `422`; categoría incompatible o archivada responde `409`;
recurso inexistente responde `404`.

### Presupuestos

- `GET /finance/budgets?month={YYYY-MM}` lista presupuestos por nombre de categoría.
- `PUT /finance/budgets/{month}/{category_id}` acepta `{"limit_minor": 250000}`. Devuelve `201` al
  crear y `200` al reemplazar el límite existente.
- `DELETE /finance/budgets/{month}/{category_id}` elimina y devuelve `204`.

Mes o límite inválidos responden `422`; categoría inexistente responde `404`; categoría de ingreso
o archivada responde `409`. Un presupuesto inexistente al eliminar responde `404`. Reemplazar un
límite no genera XP adicional.
Dos `PUT` concurrentes para el mismo mes y categoría convergen en el único presupuesto persistido.
La solicitud que pierde la carrera de inserción recupera el recurso, aplica su límite y responde
`200`; una violación de unicidad no se expone como error interno.

### Resumen

- `GET /finance/summary?month={YYYY-MM}` devuelve `MonthlySummary`.

Un mes válido sin movimientos o presupuestos devuelve ceros y `categories: []`. La ausencia de
moneda base responde `409`; un mes inválido responde `422`.

## Estados de UI

### Configuración inicial

- **Sin moneda:** una sola acción para elegir moneda y una explicación de que se bloqueará con datos.
- **Sin categorías:** después de la moneda, una acción para crear la primera categoría.
- **Conflicto de moneda:** explica que existen datos y no ofrece conversión ficticia.

### Captura de movimiento

- **Listo:** tipo, importe, categoría, fecha y descripción en ese orden; nota queda secundaria.
- **Guardando:** bloquea solo el formulario y evita reenvíos.
- **Error de validación:** se muestra junto al campo, conserva los valores y mueve foco al resumen.
- **Éxito:** cierra o limpia la captura, actualiza lista y resumen y conserva contexto del mes.
- **Sin categorías compatibles:** ofrece crear una categoría sin perder lo ya escrito.

### Presupuesto y resumen

- **Vacío mensual:** ceros reales, sin datos inventados, y acción para registrar un movimiento.
- **Sin presupuesto:** el resumen financiero sigue visible y ofrece configurar uno.
- **Con presupuesto:** límite, gasto y restante con texto además de color.
- **Límite superado:** muestra el restante negativo de forma neutral, sin alarma ni recomendación.
- **Captura secundaria:** la importación documental y el registro manual permanecen ocultos por
  defecto en un panel desplegable accesible.
- **Control financiero:** el resumen prioriza total gastado, balance, presupuesto restante y
  distribución porcentual por categoría, con comparación de hasta seis meses.
- **Filtro de periodo:** botones persistentes de enero al mes actual permiten seleccionar varios
  meses independientes; un segundo clic deselecciona el mes y el control actualiza sus indicadores,
  comparación y lista como una sola interacción.
- **Movimientos del periodo:** después del resumen aparece una lista scrolleable, ordenada por fecha
  descendente, que muestra todos los movimientos de los meses seleccionados sin crecer
  indefinidamente.
- **Exportación:** la lista puede descargarse como un archivo Excel `.xlsx` con los mismos meses
  seleccionados y orden, sin incluir notas privadas.
- **Presentación monetaria:** los importes visibles en dashboard, lista y exportación se redondean a
  unidades enteras; la precisión entera persistida en unidades menores no cambia.
- **Gestión financiera:** categorías y presupuestos se editan en una sola sección; cada categoría
  permite modificar su nombre, archivarse y, si es de gasto, configurar su límite.
- **Moneda secundaria:** la moneda base se muestra como una nota discreta; la multimoneda queda
  fuera del alcance del MVP.
- **Carga:** conserva dimensiones del encabezado, métricas y lista.
- **Error:** mensaje local y reintento; no reemplaza otros datos ya cargados.
- **Mes distinto:** el selector actualiza movimientos, presupuestos y resumen como una sola vista.

## Privacidad

- Los datos se guardan en la base local configurada; no se envían a analítica ni servicios externos.
- Las notas no aparecen en el resumen ni en el ledger de gamificación.
- Los logs de aplicación no deben incluir cuerpos de movimientos, importes, descripciones o notas.
- Exportación, copias remotas y cifrado adicional requieren especificaciones futuras explícitas.

## Criterios de aceptación

- La moneda base se crea una vez y no puede cambiar a otra cuando existen movimientos o presupuestos.
- La API rechaza importes decimales, cero, negativos o fuera del tipo entero admitido.
- Una categoría archivada conserva históricos y rechaza nuevas referencias.
- Un movimiento exige categoría compatible con `type` y persiste después de recargar.
- Listar por mes incluye exactamente las fechas civiles de ese `YYYY-MM`.
- Un presupuesto es único por mes y categoría, y `PUT` crea o reemplaza de forma determinista.
- Dos creaciones concurrentes del mismo presupuesto producen un solo recurso y respuestas
  controladas, sin `IntegrityError` expuesto.
- El resumen calcula ingresos, gastos, balance y presupuestos a partir de los datos persistidos.
- Un mes vacío devuelve ceros reales y nunca cifras de demostración.
- El MVP no expone rutas ni controles funcionales de cuentas, transferencias, bancos, importación o
  monedas múltiples.
- Ningún monto, saldo o número de movimientos genera XP; solo el primer presupuesto configurado
  puede generar el evento financiero permitido.
- Captura, edición, eliminación, presupuesto y cambio de mes son operables con teclado y foco visible.
- La captura documental y manual puede abrirse con teclado sin ocultar sus nombres o propósito.
- El control financiero muestra el total del periodo, porcentajes por categoría y comparación mensual
  sin inventar datos para meses vacíos.
- Los botones mensuales son operables con teclado, identifican el mes seleccionado y no permiten
  seleccionar meses futuros del año actual.
- Todos los botones YTD permanecen visibles; el segundo clic alterna la selección y por defecto se
  seleccionan los tres últimos meses disponibles.
- La lista limita visualmente su altura, mantiene el orden descendente y conserva edición y
  eliminación de los movimientos.
- La exportación descarga un `.xlsx` del rango seleccionado y muestra un estado recuperable si falla.
- Los importes mostrados se redondean a enteros de forma consistente, incluidos valores negativos,
  sin modificar los importes persistidos.
- Los datos financieros no aparecen en telemetría, logs de cuerpos ni respuestas ajenas al usuario.

## Decisiones registradas

- **D-004-01:** usar una moneda base singleton y bloquear su cambio cuando existan datos.
- **D-004-02:** representar dinero como unidades menores enteras según ISO 4217.
- **D-004-03:** modelar movimientos con importe positivo y dirección `income | expense`.
- **D-004-04:** exigir una categoría compatible para cada movimiento.
- **D-004-05:** archivar categorías con historial en lugar de eliminarlas físicamente.
- **D-004-06:** usar `PUT` por mes y categoría para crear o reemplazar presupuestos.
- **D-004-07:** derivar el resumen al consultar y no persistir saldos agregados.
- **D-004-08:** mantener fuera cuentas, transferencias, sincronización, importación y multimoneda.
- **D-004-09:** no registrar cuerpos ni enviar telemetría con datos financieros.
- **D-004-10:** usar lenguaje neutral y no inferir calidad moral a partir de montos o presupuestos.
- **D-004-11:** limitar la gamificación financiera al primer presupuesto y a la revisión semanal
  definida en la especificación de gamificación.
- **D-004-12:** recuperar el presupuesto persistido cuando un `PUT` pierde una inserción concurrente
  y aplicar sobre él el límite solicitado.
- **D-004-13:** mantener la importación documental como propuesta temporal, con confirmación batch
  humana y sin alterar las reglas de movimientos manuales.
- **D-004-14:** priorizar el control financiero visible y mantener la captura secundaria plegada por
  defecto; comparar seis meses mediante resúmenes mensuales ya persistidos.
- **D-004-15:** reemplazar el calendario por botones YTD del año actual y mantenerlos visibles.
- **D-004-16:** generar la exportación Excel en el backend para mantener el mismo contrato de rango,
  aislamiento por usuario y representación monetaria que la consulta financiera.
- **D-004-17:** usar selección múltiple independiente de meses, con los tres últimos meses
  disponibles seleccionados por defecto; los agregados se derivan solo de esa selección.
