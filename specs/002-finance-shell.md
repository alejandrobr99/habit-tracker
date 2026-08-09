# 002 — Shell de finanzas

## Estado

Propuesta de estructura navegable. No incluye operaciones financieras reales.

## Contexto

Finanzas necesita un punto de entrada coherente con el planificador antes de definir cuentas,
transacciones y presupuestos. Este alcance valida navegación, jerarquía y estados sin fijar un
modelo prematuramente.

## Objetivos

- Crear la ruta `/finanzas` y su navegación principal.
- Comunicar con precisión qué está disponible y qué llegará después.
- Establecer una estructura extensible para resumen, movimientos y presupuestos.
- Validar la dirección visual con datos de demostración claramente identificados.
- Evitar que controles futuros parezcan funcionales.

## No objetivos

- Persistir cuentas, saldos, transacciones, categorías o presupuestos.
- Importar archivos, conectar bancos o convertir monedas.
- Calcular patrimonio, flujo de caja, proyecciones o recomendaciones.
- Definir todavía contratos definitivos para entidades financieras.
- Mostrar cifras personales inventadas como si fueran reales.

## Modelo

No se crea un modelo persistente en esta entrega. La UI puede usar un tipo local de presentación:

| Campo | Tipo | Uso |
| --- | --- | --- |
| `period_label` | string | Periodo visible, por ejemplo “Agosto de 2026” |
| `currency` | string | Código ISO 4217 configurado para la demostración |
| `income_minor` | entero | Dato de demostración |
| `expense_minor` | entero | Dato de demostración |
| `balance_minor` | entero | Dato de demostración |
| `is_demo` | booleano | Siempre `true` en este alcance |

Los valores se mantienen en unidades menores enteras y se formatean con `Intl.NumberFormat`. No
deben enviarse al backend ni sobrevivir a una recarga como datos del usuario.

## API

No se añade un endpoint financiero. El shell puede consultar únicamente:

- `GET /api/v1/health` para el estado general de la aplicación, si la composición lo requiere.

Las rutas anticipadas como `/accounts` o `/transactions` no deben implementarse vacías. La
especificación del primer recurso financiero deberá definir antes su modelo, invariantes, errores
y privacidad.

## Estructura de interfaz

### Encabezado

- Título “Finanzas” y texto que indique que es una vista inicial.
- Selector de periodo visible pero deshabilitado, acompañado de “Próximamente”.
- Ningún botón primario para crear datos mientras no exista persistencia.

### Resumen de demostración

- Tres tarjetas: ingresos, gastos y balance.
- Etiqueta persistente “Datos de demostración”.
- Valores estables, plausibles y sin animaciones.
- Una nota explica que no representan información del usuario.

### Navegación interna

- “Resumen” aparece como sección activa.
- “Movimientos” y “Presupuestos” se muestran como destinos no disponibles solo si ayudan a
  validar arquitectura; no son enlaces interactivos.
- En pantallas pequeñas, las secciones mantienen orden de lectura y no dependen de desplazamiento
  horizontal.

### Próximo paso

Un bloque final describe que la siguiente entrega permitirá registrar movimientos manualmente.
No incluye formulario, modal ni llamada a la acción falsa.

## Estados de UI

- **Listo:** shell completo con cifras y etiqueta de demostración.
- **Carga de aplicación:** esqueleto del encabezado y tres tarjetas, sin cifras parciales.
- **Backend no disponible:** aviso no bloqueante; el contenido demostrativo sigue visible.
- **Viewport estrecho:** tarjetas apiladas y navegación con ajuste de línea.
- **Función futura:** control deshabilitado con texto visible; no depender solo de `title`.
- **Error inesperado:** límite de error local con opción de reintentar la vista.

No existe un estado vacío de datos del usuario porque todavía no se solicitan ni persisten datos.

## Criterios de aceptación

- `/finanzas` es accesible desde la navegación principal y conserva el destino activo.
- La página se identifica inequívocamente como shell y todos los importes como demostración.
- No se realizan solicitudes a endpoints financieros inexistentes.
- No hay controles que acepten datos ni aparenten guardar cambios.
- Los destinos futuros no reciben foco si no son interactivos.
- El layout funciona desde 320 px sin desplazamiento horizontal.
- Importes y fechas se formatean con APIs de internacionalización, no por concatenación manual.
- Los colores de ingresos, gastos y balance no son el único medio para distinguirlos.

## Decisiones registradas

- **D-002-01:** validar primero la arquitectura visual y no diseñar persistencia especulativa.
- **D-002-02:** usar datos de demostración explícitos en lugar de una pantalla vacía engañosa.
- **D-002-03:** mantener funciones futuras visibles solo cuando aclaren la estructura prevista.
- **D-002-04:** no crear endpoints de marcador de posición.
- **D-002-05:** posponer categorías, cuentas y monedas múltiples a especificaciones separadas.

## Preguntas abiertas

- ¿El primer incremento funcional será captura de movimientos o definición de cuentas?
- ¿La moneda base pertenece al perfil general o al dominio financiero?
- ¿Qué datos financieros deben cifrarse cuando se defina persistencia real?
