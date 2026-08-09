---
name: planner-design
description: Diseña, implementa y revisa interfaces del planificador conservando su dirección visual cálida, sobria y accesible. Usar al trabajar en componentes, páginas, estilos, estados de UI o contenido del frontend.
---

# Diseño del planificador

## Fuente de verdad

Lee antes de diseñar:

1. `specs/design-system.md`.
2. `specs/000-product-foundation.md`.
3. La especificación numerada de la función afectada.
4. `planner-visual-delight/SKILL.md` al diseñar movimiento, celebración u ornamento.

Si falta un estado o comportamiento, actualiza la especificación antes de inventarlo en código.

## Dirección visual

Conserva una herramienta personal espectacular pero elegante, orgánica y calmada:

- Fondos piedra cálida, superficies claras y texto carbón oliváceo.
- Verde profundo como acento principal y tonos botánicos, arcilla o dorado apagado para hitos.
- Serif editorial solo para títulos; sans serif para controles y datos.
- Bordes sutiles antes que sombras; radios moderados y espacio generoso.
- Una acción primaria por región y jerarquía de lectura evidente.
- Motivos botánicos abstractos que no compitan con texto ni controles.
- Movimiento breve y funcional según `planner-visual-delight`.

Evita negro puro, colores neón, emojis, escenas decorativas, exceso de tarjetas, sombras dramáticas,
navegación de panel genérico y celebraciones invasivas o no reducibles.

## Flujo de trabajo

1. Enumera el objetivo, la tarea principal y los criterios de aceptación aplicables.
2. Define carga, vacío, contenido, error, guardado, éxito y conflicto cuando correspondan.
3. Construye primero la jerarquía semántica y el orden de foco.
4. Aplica únicamente tokens del sistema de diseño.
5. Verifica 320, 768, 1024 y 1440 px sin desplazamiento horizontal.
6. Revisa teclado, foco, contraste, nombres accesibles y movimiento reducido.
7. Contrasta el resultado con los criterios de aceptación y registra cualquier decisión nueva.

## Reglas de composición

- Limita el contenido a 1480 px y el texto largo a 68 caracteres por línea.
- Mantén controles de al menos 48 × 48 px.
- No uses color como único indicador.
- No ocultes una función esencial detrás de hover.
- Los controles no disponibles deben parecerlo y explicar su estado en texto visible.
- Una tarjeta agrupa contenido relacionado; no es el contenedor predeterminado.
- En móvil, preserva orden de lectura y contexto antes que densidad.

## Contenido

Escribe en español claro y no moralizante. Usa acciones específicas como “Crear hábito” y estados
neutrales como “Pendiente” u “Omitido”. Los errores explican qué ocurrió y cómo recuperarse. Los
datos de demostración permanecen etiquetados mientras estén visibles.

## Revisión final

- La pantalla coincide con la especificación funcional.
- Todos los estados necesarios están representados.
- Los tokens y componentes mantienen la dirección visual.
- El flujo completo funciona con teclado y foco visible.
- La interfaz es comprensible sin color y con movimiento reducido.
- No hay funciones ficticias, acciones ambiguas ni estilos fuera del sistema.
