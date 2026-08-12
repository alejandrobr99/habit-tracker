---
name: personal-finance
description: Diseña, implementa y revisa funciones de finanzas personales privadas, exactas y neutrales. Se usa automáticamente al trabajar con moneda, unidades menores, categorías, movimientos, ingresos, gastos, presupuestos, resúmenes, captura financiera o futuras integraciones.
---

# Finanzas personales

## Fuente de verdad

Lee primero `specs/004-finance-mvp.md`. Consulta `specs/000-product-foundation.md` solo si el
cambio afecta convenciones comunes o alcance. Consulta `specs/design-system.md` si cambia la
interfaz, `specs/003-gamification.md` si produce reconocimiento y [REFERENCE.md](REFERENCE.md)
si afecta representación monetaria, privacidad o integraciones futuras.

`specs/002-finance-shell.md` es contexto histórico, no el contrato del MVP. Si falta un
comportamiento, actualiza la especificación antes de inventarlo en código.

## Principios

- Exactitud antes que conveniencia: importes enteros en unidades menores y códigos ISO 4217.
- Captura rápida sin perder validación: tipo, importe, categoría, fecha y descripción primero.
- Privacidad local: minimiza datos, evita logs de cuerpos y no introduce servicios externos.
- Neutralidad: describe saldos, límites y diferencias sin juzgar decisiones personales.
- Alcance explícito: no anticipa cuentas, transferencias, bancos, importación ni multimoneda.
- Separación de dominios: finanzas emite solo los eventos permitidos hacia gamificación.

## Reglas obligatorias

- Nunca uses `float` para dinero.
- Nunca infieras moneda por locale; usa el singleton configurado.
- Valida código y exponente con un catálogo ISO 4217 actual.
- Un importe de movimiento es positivo; `type: income | expense` determina su dirección.
- Exige categoría activa y compatible.
- Calcula el mes por la fecha civil del movimiento.
- Deriva resumen y presupuesto desde datos persistidos; no mantengas un saldo duplicado.
- No registres importes, descripciones o notas en logs, telemetría o errores.
- No otorgues XP por monto, ahorro, saldo o cantidad de movimientos.

## Flujo de trabajo

1. Enumera criterios de aceptación y límites del incremento.
2. Revisa moneda, precisión, signo, fecha civil y reglas de categoría.
3. Define contratos HTTP con cuerpo, respuesta, validación, ausencia y conflicto.
4. Mantén transacciones de base de datos cortas y atómicas para cada mutación.
5. Diseña configuración inicial, captura, vacío, carga, error y conflicto.
6. Revisa exposición de datos en logs, analítica, fixtures y mensajes.
7. Prueba cálculos con cero, límites, meses y categorías archivadas.
8. Confirma que no aparecieron conceptos fuera de alcance.

## Captura y presentación

- Acepta entrada humana formateada en UI, pero conviértela a entero antes de llamar a la API.
- Muestra moneda con `Intl.NumberFormat` y el exponente ISO correspondiente.
- Conserva valores del formulario ante validación o fallo recuperable.
- No uses rojo como único indicador ni para moralizar un gasto.
- Un límite superado se expresa como dato: “Restante: -$…”, no como fracaso.
- Un mes vacío muestra ceros reales y una acción clara, nunca cifras inventadas.
- Evita pedir notas o detalles no necesarios para el resumen.

## Verificación

- Rechaza decimal JSON, cero, negativo, desbordamiento y moneda inválida.
- Bloquea cambio de moneda cuando existen movimientos o presupuestos.
- Conserva históricos al archivar una categoría.
- Impide categorías incompatibles en creación y edición.
- Verifica límites de mes, orden estable y cálculo `income - expense`.
- Comprueba presupuesto sin movimientos, exacto, restante positivo y restante negativo.
- Revisa teclado, foco, escalas objetivo y significado independiente del color.
- Inspecciona que logs y eventos de gamificación no contengan datos financieros.
