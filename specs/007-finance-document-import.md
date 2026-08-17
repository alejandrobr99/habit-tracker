# 007 — Importación de documentos financieros con Gemini

## Estado

Primera versión implementable. Extiende el MVP financiero sin convertir el
documento original en un adjunto permanente ni crear movimientos automáticamente.

## Objetivos

- Recibir un recibo o extracto en JPEG, PNG o PDF con sesión activa.
- Enviar una representación normalizada del documento a `gemini-3.1-flash-lite` mediante el backend.
- Devolver propuestas en una estructura fija de cuatro campos: fecha, descripción, valor de transacción
  y categoría.
- Permitir corregir cada propuesta y crear categorías nuevas antes de confirmar.
- Confirmar todas las filas válidas en una sola operación atómica.
- Derivar el resumen mensual y el desglose por categoría desde movimientos persistidos.
- Limitar el coste y evitar que datos financieros lleguen a logs o al frontend.

## No objetivos

- Sin sincronización bancaria, cuentas, conciliación, extracción automática de comercios o reglas
  recurrentes.
- Sin persistencia del archivo original, texto OCR, prompt o respuesta del proveedor.
- Sin llamada desde el navegador al proveedor ni clave en el frontend.
- Sin confirmación automática, reintentos automáticos ni procesamiento en segundo plano.
- Sin prometer exactitud para documentos ilegibles, manuscritos o formatos no aceptados.

## Decisiones

- **D-007-01:** usar `gemini-3.1-flash-lite` estable por ser el modelo multimodal de menor coste
  adecuado para extracción sencilla, con imagen, PDF y salida estructurada.
- **D-007-02:** usar datos inline normalizados y no Files API; la copia local se elimina al terminar.
- **D-007-03:** exigir una propuesta estructurada y confirmación humana antes de persistir.
- **D-007-04:** conservar dos límites de coste: prepago de USD 10 en el proveedor y presupuesto
  interno persistente de USD 10 con reserva antes de cada llamada.
- **D-007-05:** bloquear el análisis cuando falte `GEMINI_API_KEY`; no degradar silenciosamente a un
  proveedor diferente.
- **D-007-06:** guardar únicamente hash del documento confirmado y metadatos de coste, nunca el
  contenido financiero.
- **D-007-07:** aceptar la transferencia a Google solo después de consentimiento explícito visible.
- **D-007-08:** sugerir `domicilio` para comercios identificados como Rappi y `transporte` para
  Uber, Cabify o DiDi, siempre que esas categorías existan para la cuenta.

## Límites

| Recurso | Límite |
| --- | --- |
| Tamaño recibido | 10 MiB |
| Páginas PDF | 10 |
| Dimensiones rasterizadas | 20 megapíxeles por página |
| Filas propuestas | 200 |
| Análisis por cuenta | 5 por hora |
| Análisis concurrentes | 1 por cuenta y 2 por instancia |
| Tiempo de proveedor | 45 segundos |
| Presupuesto interno | USD 10, expresado en microdólares |

El prepago del proveedor detiene el servicio al llegar a cero, aunque la medición puede dejar un
saldo ligeramente negativo por latencia. El presupuesto interno reserva el coste máximo permitido
antes de llamar al proveedor y falla cerrado ante una respuesta incierta.

## Modelo

### OcrImport

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | integer | Generado por la base |
| `user_id` | integer | Propietario derivado de la sesión |
| `document_hash` | string | SHA-256 de la representación recibida |
| `model` | string | Identificador estable del modelo |
| `input_tokens` | integer | Metadato del proveedor |
| `output_tokens` | integer | Metadato del proveedor |
| `cost_microusd` | integer | Coste estimado no negativo |
| `status` | enum | `confirmed` |
| `created_at` | datetime | UTC |

La unicidad es `(user_id, document_hash)`. El registro se crea en la misma transacción que las
transacciones confirmadas.

### ProposedTransaction

No se persiste. Vive únicamente en la respuesta de previsualización y en el estado del cliente:

| Campo | Tipo | Regla |
| --- | --- | --- |
| `row_id` | string | Identificador opaco generado por el servidor |
| `type` | enum | `income` o `expense` |
| `amount_minor` | integer o null | Positivo tras interpretar el texto monetario con la moneda base |
| `date` | date o null | Fecha civil válida |
| `description` | string o null | 1 a 120 caracteres |
| `category_id` | integer o null | Categoría activa del usuario |
| `category_name` | string o null | Sugerencia no confiable |
| `confidence` | enum | `high`, `medium`, `low` |
| `field_errors` | objeto | Errores deterministas por campo |

## API

Todas las rutas usan `/api/v1`, sesión activa y mensajes de error genéricos.

- `POST /finance/imports/preview` recibe un único `multipart/form-data` con `file` y devuelve
  `OcrPreviewRead`. El backend valida sesión, frecuencia, tamaño, firma, estructura y cotas antes de
  enviar contenido. La respuesta incluye `import_token`, filas, advertencias, modelo y coste reservado.
- `POST /finance/imports/{import_token}/confirm` recibe exactamente las filas editadas y devuelve
  `OcrConfirmRead` con los movimientos creados. Revalida usuario, categorías, importes, fechas,
  descripciones y reserva. Una fila inválida produce `422` y ninguna fila se guarda. El máximo es
  200 filas por importación.
- `GET /finance/imports/budget` devuelve presupuesto usado, reservado y restante sin contenido de
  documentos.

La confirmación solo acepta un token de previsualización de corta duración, ligado al usuario y a un
hash de propuesta en memoria del proceso. El archivo nunca se vuelve descargable.

## Seguridad y privacidad

- El backend normaliza JPEG/PNG con Pillow y PDF con PyMuPDF, eliminando metadatos y contenido activo
  antes de la llamada. Se rechazan SVG, HTML, archivos comprimidos, PDF con JavaScript, acciones,
  formularios o archivos incrustados.
- El documento normalizado viaja a Google como contenido no confiable separado de las instrucciones.
  El modelo no recibe herramientas, secretos, identificadores internos ni datos de otras cuentas.
- La salida se valida con JSON Schema y después con las reglas manuales. No se repara una respuesta
  fuera de esquema con heurísticas.
- El proveedor devuelve el importe tal como aparece impreso. El backend interpreta separadores de
  miles y decimales según su estructura y la moneda base: dos cifras finales pueden ser decimales;
  tres cifras finales son agrupación de miles. Para COP, un resultado inferior a 1.000 se marca para
  revisión humana en lugar de aceptarse silenciosamente.
- La interfaz informa que el documento sale de la instancia. En el plan pagado, Google no usa prompts,
  archivos ni respuestas para mejorar productos, pero puede conservarlos temporalmente para seguridad
  u obligaciones legales.
- No se registran archivo, texto, prompt, respuesta, importe, descripción, categoría ni clave.
- `GEMINI_API_KEY` solo existe en el backend y se configura como secreto del entorno.

## Estados de UI

- **Disponible:** acción de importar y aviso de transferencia a Google.
- **Seleccionando:** acepta solo JPEG, PNG o PDF y muestra el límite.
- **Analizando:** bloquea el envío y no reintenta automáticamente.
- **Revisión:** tabla con cuatro campos editables, errores por fila, eliminación de filas y creación de
  categoría.
- **Sin propuestas válidas:** explica que se puede cancelar y probar otro documento.
- **Presupuesto agotado:** no ofrece reintentar.
- **Límite horario:** informa que se alcanzó el límite temporal de análisis y responde `429`;
  no se presenta como presupuesto agotado.
- **Proveedor no configurado:** instrucción de administración, sin detalle de configuración interna.
- **Proveedor temporalmente no disponible:** ofrece reintentar más tarde y libera la reserva interna.
- **Confirmando:** bloquea solo la revisión actual.
- **Éxito:** actualiza movimientos, resumen y desglose mensual.

## Reportería

El dashboard conserva cuatro indicadores: gastos, balance, categoría con mayor gasto y presupuesto
restante. El desglose lista categorías de gasto con importe y proporción textual, sin usar color como
único indicador ni inferir calidad sobre las decisiones.

## Criterios de aceptación

- Una persona autenticada puede previsualizar JPEG, PNG y PDF dentro de las cotas.
- El proveedor nunca se llama si la firma, estructura, tamaño o presupuesto son inválidos.
- La clave nunca aparece en respuestas, código generado del frontend o logs.
- Una respuesta fuera del esquema o con datos inválidos se descarta de forma controlada.
- `$6,100` en COP se propone como 6.100 pesos, no como 61; formatos equivalentes con punto o coma se
  interpretan sin usar `float`.
- Un fallo temporal del proveedor responde `503`, no consume presupuesto interno y no se presenta
  como un documento o una respuesta inválidos.
- El límite horario responde `429` y el presupuesto interno agotado responde `409`, con mensajes
  diferenciados.
- Una propuesta no crea movimientos antes de la confirmación explícita.
- La tabla siempre permite editar fecha, descripción, valor y categoría.
- Una persona puede eliminar una fila propuesta antes de confirmar; las filas eliminadas no se guardan.
- Una categoría nueva puede crearse durante la revisión sin perder otras filas.
- La confirmación crea todas las filas o ninguna y revalida categorías e importes.
- Un documento confirmado dos veces responde `409` sin duplicar movimientos.
- Un usuario no puede consultar ni confirmar una importación ajena.
- El presupuesto interno rechaza nuevas llamadas al agotarse y no se incrementa con errores previos
  a la llamada.
- Ningún log o error contiene contenido financiero.
- El resumen mensual incluye los movimientos confirmados y el desglose por categoría.

