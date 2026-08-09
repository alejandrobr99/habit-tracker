# Investigación para deleite visual responsable

## Alcance

Esta síntesis convierte evidencia de motivación, color, microinteracciones y accesibilidad en reglas
de diseño. No diagnostica, no garantiza cambio conductual y no convierte engagement en bienestar.

## Recompensa inmediata y persistencia

Woolley y Fishbach encontraron que el disfrute y otras recompensas inmediatas predicen mejor la
persistencia durante actividades orientadas a metas que sus beneficios demorados. La implicación
prudente no es “más premios producen hábitos”, sino hacer agradable y comprensible el momento de la
acción elegida.

Aplicación:

- responder inmediatamente después de una mutación confirmada;
- reconocer la acción concreta, no una identidad o resultado futuro;
- mantener el feedback cerca del control y permitir continuar;
- no aumentar duración, ruido o valor del premio para forzar repetición.

Fuentes:

- Woolley, K. y Fishbach, A. (2017), “Immediate Rewards Predict Adherence to Long-Term Goals”,
  [Personality and Social Psychology Bulletin](https://doi.org/10.1177/0146167216676480).
- Woolley, K. y Fishbach, A. (2016), “For the Fun of It: Harnessing Immediate Rewards to Increase
  Persistence in Long-Term Goals”,
  [Journal of Consumer Research](https://doi.org/10.1093/jcr/ucv098).

## Autonomía y motivación sostenida

Self-Determination Theory distingue autonomía, competencia y conexión real. La gamificación puede
apoyar motivación cuando ofrece elección y feedback de dominio; puede controlarla cuando condiciona
la tarea a premios, pérdida o aprobación.

Aplicación:

- el usuario elige hábitos, desafíos y recompensas;
- XP y rachas permanecen secundarios;
- el feedback explica progreso verificable;
- sin avatares, rivales o aprobación social ficticia;
- no usar animación para crear miedo a perder continuidad.

Fuentes:

- Ryan, R. M. y Deci, E. L. (2000), “Self-determination theory and the facilitation of intrinsic
  motivation, social development, and well-being”,
  [American Psychologist](https://doi.org/10.1037/0003-066X.55.1.68).
- Alberts, L., Lyngs, U. y Lukoff, K. (2024), “Designing for Sustained Motivation: A Review of
  Self-Determination Theory in Behaviour Change Technologies”,
  [Interacting with Computers](https://doi.org/10.1093/iwc/iwae040).

## Rachas y recuperación

Una racha intacta puede aumentar intención de continuar; una ruptura atribuida a la persona puede
reducirla. La posibilidad de reparación atenúa el efecto. Esto justifica continuidad transparente,
no amenazas ni borrado del historial.

Aplicación:

- mostrar la racha como descripción, no como deuda;
- ofrecer “Continuar hoy” aunque no haya recuperación;
- distinguir recuperación de check-in;
- no otorgar XP o celebración de logro por reparar.

Fuente:

- Silverman, J. y Barasch, A. (2023), “On or Off Track: How (Broken) Streaks Affect Consumer
  Decisions”, [Journal of Consumer Research](https://doi.org/10.1093/jcr/ucad021).

## Animación útil y deleite

Nielsen Norman Group recomienda movimiento breve y discreto para feedback, cambio de estado y
modelo espacial. El deleite superficial no compensa una experiencia poco fiable o lenta. La mayoría
de animaciones de interfaz funciona entre 100 y 500 ms; la duración más corta que sigue siendo
legible suele ser preferible.

Aplicación:

- cada animación tiene evento, mensaje y final;
- usar easing de salida para respuesta perceptible y asentamiento suave;
- evitar animaciones repetitivas en tareas frecuentes;
- lograr riqueza por composición y capas, no por demora;
- probar la tarea completa antes de valorar ornamentación.

Fuentes:

- Nielsen Norman Group, [The Role of Animation and Motion in UX](https://www.nngroup.com/articles/animation-purpose-ux/).
- Nielsen Norman Group, [Executing UX Animations: Duration and Motion Characteristics](https://www.nngroup.com/articles/animation-duration/).
- Nielsen Norman Group, [Microinteractions in User Experience](https://www.nngroup.com/articles/microinteractions/).
- Nielsen Norman Group, [A Theory of User Delight](https://www.nngroup.com/articles/theory-user-delight/).

## Color contextual, no universal

Una revisión de 132 estudios encontró asociaciones sistemáticas entre color y emoción, moduladas por
luminosidad, saturación y contexto. Los autores advierten que una asociación abstracta no demuestra
que el color produzca esa emoción en una interfaz concreta.

Aplicación:

- verde y azul verdoso pueden sostener un tono calmado;
- dorado apagado y tonos claros pueden señalar celebración;
- alta saturación se reserva para atención puntual, no para superficies persistentes;
- no describir una paleta como mecanismo para “crear” una conducta;
- duplicar toda señal con forma, icono y texto.

Fuente:

- Jonauskaite et al. (2024), “Do we feel colours? A systematic review of 128 years of psychological
  research linking colours and emotions”,
  [Psychonomic Bulletin & Review](https://doi.org/10.3758/s13423-024-02615-z).

## Movimiento y accesibilidad

WCAG 2.2 exige que el movimiento no esencial activado por interacción pueda suprimirse. W3C
recomienda `prefers-reduced-motion`; Apple propone sustituir profundidad, parallax, giro y movimiento
multieje por disolución, resaltado o cambio de color cuando el movimiento comunica estado.

Aplicación:

- diseñar una confirmación estática equivalente;
- habilitar movimiento con `prefers-reduced-motion: no-preference` cuando sea viable;
- eliminar partículas, escala y desplazamiento en modo reducido;
- conservar contexto con texto, borde, icono y color;
- evitar parallax, desenfoque animado, giro, estrobo y autoplay.

Fuentes:

- W3C, [Understanding Success Criterion 2.3.3: Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions).
- W3C, [C39: Using the CSS prefers-reduced-motion query](https://www.w3.org/WAI/WCAG22/Techniques/css/C39).
- Apple, [Reduced Motion evaluation criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/reduced-motion-evaluation-criteria/).

## Criterio de adopción

Antes de añadir un efecto:

1. Identificar el cambio real que comunica.
2. Confirmar que ocurre después del éxito.
3. Explicar qué necesidad apoya sin controlar al usuario.
4. Elegir el nivel de feedback mínimo que sigue siendo satisfactorio.
5. Definir alternativa estática y final de la animación.
6. Revisar frecuencia, foco, contraste y siguiente acción.
7. Rechazarlo si depende de pérdida, urgencia, azar, comparación u opacidad.
