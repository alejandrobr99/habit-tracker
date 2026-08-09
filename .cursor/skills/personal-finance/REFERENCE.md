# Referencia de finanzas personales

## Dinero y unidades menores

ISO 4217 define códigos alfabéticos de tres letras y la relación decimal entre una moneda y su
unidad menor. El exponente no es siempre dos: una implementación correcta obtiene el valor del
catálogo, no asume “centavos”.

Representación:

- Persistir y transportar `amount_minor` como entero.
- Mantener el código de moneda en la configuración singleton del MVP.
- Convertir texto de UI a entero con el exponente de la moneda antes de enviar.
- Rechazar `float` y JSON decimal, incluso si el valor parece exacto.
- Formatear para presentación con APIs de internacionalización y locale de interfaz.
- Validar rango antes de sumar para evitar desbordamiento del tipo persistido.

Ejemplos:

- `COP 12 345` con exponente 2 se representa como `1234500`.
- `JPY 12 345` con exponente 0 se representa como `12345`.
- El signo no forma parte del importe del movimiento; `type` define ingreso o gasto.

Fuente primaria:

- International Organization for Standardization,
  [ISO 4217 — Currency codes](https://www.iso.org/iso-4217-currency-codes.html).

## Cálculos del MVP

Para un mes civil:

```text
income_minor = suma(amount_minor donde type = income)
expense_minor = suma(amount_minor donde type = expense)
balance_minor = income_minor - expense_minor
budget_remaining_minor = budgeted_minor - gastos de categorías presupuestadas
```

No persistas estos agregados. Una consulta directa mantiene una única fuente de verdad con el
volumen esperado. Si el rendimiento real deja de ser suficiente, mide antes de introducir
materialización o caché.

## Captura rápida

Orden recomendado:

1. `type`
2. `amount_minor`
3. `category_id`
4. `date`
5. `description`
6. `note`, opcional y secundaria

La rapidez procede de reducir decisiones y conservar contexto, no de omitir validación:

- Predetermina la fecha local actual, pero mantenla visible y editable.
- Filtra categorías por tipo.
- Conserva el formulario si falla la red o validación.
- Tras guardar, devuelve foco a un punto predecible y actualiza el mes visible.
- No solicites comercio, cuenta, adjunto o etiqueta en el MVP.
- No hagas actualización optimista si puede mostrar un resumen monetario que el servidor rechazó.

## Privacidad local

Los datos financieros revelan comportamiento y contexto personal aunque no incluyan identidad
explícita. Minimiza colección y superficies de exposición:

- No envíes telemetría de importes, categorías, descripciones, notas o presupuestos.
- No registres cuerpos HTTP financieros ni consultas con datos sensibles.
- Usa datos sintéticos inequívocamente etiquetados en pruebas y capturas.
- Devuelve errores estructurales sin repetir el valor privado rechazado.
- Limita consultas al usuario implícito; autenticación futura no sustituye autorización por recurso.
- Documenta ubicación y copia de seguridad de la base antes de prometer “solo local”.
- No afirmes cifrado en reposo si depende únicamente del disco o sistema operativo.

Guía relacionada:

- OWASP,
  [Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html),
  recomienda excluir o enmascarar datos sensibles y evitar que los logs se conviertan en otra base
  de datos privada.

## Neutralidad

- Describe hechos: “Gastado”, “Límite”, “Restante”, “Sin presupuesto”.
- No clasifiques gastos como buenos, malos, responsables o impulsivos.
- No infieras salud financiera, disciplina o éxito a partir del balance.
- No uses rojo, vibración, culpa o urgencia para un límite superado.
- No propongas recortes ni asesoría sin una especificación y contexto adecuados.
- La gamificación reconoce configuración y revisión, nunca riqueza, ahorro o actividad.

## Integraciones futuras

No agregues abstracciones de integración durante el MVP. Cuando exista una especificación aceptada,
cada integración debe resolver explícitamente:

### Importación de archivos

- Formato y versión admitidos.
- Vista previa y confirmación antes de persistir.
- Clave idempotente o huella para evitar duplicados.
- Mapeo explícito de moneda, fecha, signo y categoría.
- Provenance del registro importado sin conservar el archivo más tiempo del necesario.
- Informe de filas aceptadas, rechazadas y ambiguas.

### Sincronización bancaria

- Consentimiento específico, revocable y con alcance mínimo.
- OAuth 2.0 con Authorization Code y PKCE cuando el proveedor lo permita; nunca credenciales
  bancarias capturadas por el planificador.
- Tokens fuera de logs, cifrados en reposo y con rotación o revocación definida.
- Identidad estable del proveedor para idempotencia y actualización.
- Estados explícitos de pendiente, contabilizado, eliminado y corregido.
- Zona horaria, moneda original y precisión sin conversión silenciosa.
- Borrado local y desconexión del proveedor como operaciones separadas y comprensibles.

Referencias:

- IETF, [RFC 9700: Best Current Practice for OAuth 2.0 Security](https://www.rfc-editor.org/rfc/rfc9700).
- IETF, [RFC 7636: Proof Key for Code Exchange](https://www.rfc-editor.org/rfc/rfc7636).

### Multimoneda

- Moneda original por movimiento y regla explícita para reportar en moneda base.
- Fuente, instante y precisión de la tasa de cambio.
- Política ante correcciones y días sin tasa.
- Separación entre importe original y convertido.
- Prohibición de reescribir importes históricos por una tasa nueva.

### Cuentas y transferencias

- Saldo inicial y fecha efectiva.
- Transferencia como relación atómica entre dos lados, no ingreso y gasto independientes.
- Eliminación y edición que preserven consistencia.
- Conciliación y estado de movimiento antes de prometer saldo bancario.

Estas necesidades futuras no justifican hoy un repositorio genérico, un proveedor intercambiable,
campos nulos ni endpoints de marcador de posición.
