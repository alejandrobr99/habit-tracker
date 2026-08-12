---
name: planner-visual-delight
description: Diseña e implementa movimiento, microinteracciones, celebraciones y ornamentación funcional del planificador. Se usa automáticamente al trabajar con animaciones, feedback de check-in, rachas, progreso, insignias, recompensas, color expresivo, motivos orgánicos o deleite visual.
---

# Deleite visual del planificador

## Fuente de verdad

Lee primero `specs/design-system.md`. Consulta `specs/003-gamification.md` para reconocimiento,
`specs/001-habit-tracker.md` para check-ins o rachas y [RESEARCH.md](RESEARCH.md) solo cuando se
justifique una mecánica, color o intensidad.

Usa `planner-design` para composición estática y `planner-gamification` para reglas de dominio. Esta
skill define cómo se expresa visualmente un cambio real.

## Resultado buscado

La experiencia se siente espectacular pero elegante, orgánica y calmada. El deleite refuerza
comprensión, competencia y continuidad; nunca secuestra atención ni convierte la interfaz en premio.

## Flujo de trabajo

1. Identifica el evento confirmado, la tarea siguiente y el criterio de aceptación.
2. Clasifica el feedback como microrespuesta, celebración local o celebración de hito.
3. Diseña primero la confirmación estática y después el movimiento.
4. Usa únicamente tokens documentados de color, forma y duración.
5. Activa el efecto después del éxito; nunca celebres una mutación pendiente o fallida.
6. Conserva foco, navegación, lectura y posibilidad de repetir otra acción de inmediato.
7. Implementa la alternativa `prefers-reduced-motion`.
8. Verifica teclado, lector de pantalla, contraste, escala de grises y repetición frecuente.

## Niveles de feedback

### Microrespuesta

Para presión, hover, foco y selección. Usa `motion-instant` o `motion-state`. Cambia borde, fondo,
opacidad o escala mínima. No añade texto ni partículas.

### Celebración local

Para un check-in ordinario confirmado. Permanece junto al control que lo originó:

- marca dibujada o revelada;
- onda o halo local de una sola ejecución;
- progreso actualizado;
- texto breve anunciado con `role="status"`.

No abre modal, no mueve foco y no se reproduce al desmarcar.

### Celebración de hito

Para nivel, insignia, desafío o recompensa confirmados. Puede combinar superficie, símbolo y
partículas orgánicas durante `motion-celebration`. Es descartable, no bloqueante y no se repite al
recargar un estado ya conocido.

### Celebración escénica

Para los hitos de racha y meta definidos en `specs/003-gamification.md`. Puede ocupar el viewport
durante `motion-spectacle` con velo, rayos, órbitas, emblema y partículas finitas. No captura puntero
salvo el cierre, desaparece automáticamente y se convierte en una confirmación estática con
movimiento reducido.

## Lenguaje visual

- Usa piedra, carbón oliváceo y verde profundo como base.
- Reserva musgo, arcilla, pétalo y dorado apagado para continuidad e hitos.
- El dorado comunica reconocimiento solo acompañado de icono y texto.
- Usa formas de semilla, hoja, órbita, arco y pétalo como abstracciones; evita mascotas y escenas.
- Los lavados radiales son fondo atmosférico, nunca superficie de lectura ni indicador de estado.
- Una composición puede ser rica por capas, escala y ritmo sin aumentar el número de acciones.

## Movimiento

- Anima `opacity` y `transform`; evita propiedades que recalculen layout.
- Empieza rápido y termina con suavidad mediante easing de salida.
- Mantén las partículas cerca del origen y limita cada secuencia a una ejecución.
- Evita rebote repetitivo, parallax, giros, destellos, estrobo y autoplay.
- No retrases una mutación, navegación o siguiente check-in para mostrar una animación.
- Si una interacción se repite muchas veces, reduce la amplitud antes que aumentar duración.

## Movimiento reducido

Con `prefers-reduced-motion: reduce`:

- elimina partículas, desplazamiento, giro y escala;
- conserva texto, marca, borde y cambio de color;
- no ocultes información que en modo normal aparece durante la animación;
- no reemplaces una celebración por silencio: muestra una confirmación estática.

## Psicología conductual ética

- Apoya autonomía: el usuario elige hábito, desafío y recompensa.
- Apoya competencia: explica qué cambió y muestra progreso honesto.
- Usa recompensa inmediata como feedback de la acción, no como promesa de transformación.
- Trata la racha como continuidad descriptiva y recuperable, no como algo que debe protegerse.
- Nunca uses culpa, pérdida, urgencia, comparación, premio aleatorio o recompensa variable.
- No atribuyas virtud, disciplina, salud ni identidad personal a un logro.
- No optimices tiempo en pantalla o frecuencia de apertura como sustituto de bienestar.

## Matriz de eventos

| Evento | Feedback permitido | No usar |
| --- | --- | --- |
| Check-in creado | Celebración local | Modal, confeti global |
| Racha o meta alcanzada | Celebración escénica | Repetición continua, bloqueo |
| Check-in eliminado | Confirmación funcional | Celebración |
| Racha recuperada | Restauración estática o halo suave | Check-in falso, XP |
| Nivel alcanzado | Celebración de hito | Bloqueo de navegación |
| Insignia obtenida | Medallón y celebración de hito | Rareza artificial |
| Desafío completado | Progreso completo y celebración | Presión temporal |
| Desafío expirado | Estado neutral | Pérdida visual |
| Recompensa canjeada | Celebración de hito con su nombre | Monedas o premio aleatorio |
| Error | Mensaje recuperable | Sacudida, vergüenza |

## Verificación

- El efecto corresponde a una respuesta exitosa y a un evento especificado.
- El mismo estado no se celebra de nuevo por render o recarga.
- Desmarcar y fallar no reproducen reconocimiento.
- Foco y orden DOM no cambian por decoración.
- Las formas decorativas usan `aria-hidden="true"`.
- Color, icono y texto transmiten el estado de forma redundante.
- La animación termina dentro del token previsto y no queda movimiento continuo.
- El resultado completo funciona con movimiento reducido.
