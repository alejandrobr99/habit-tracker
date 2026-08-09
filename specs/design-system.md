# Sistema de diseño

## Dirección

La interfaz debe sentirse espectacular pero elegante, orgánica y cercana: una herramienta personal
que celebra sin competir por atención. La calidez procede de fondos minerales, tipografía cuidada,
acentos terrosos y formas botánicas abstractas. Se evita la estética genérica de panel SaaS.

## Principios

1. **Serenidad viva:** pocos niveles simultáneos, aire suficiente y movimiento con propósito.
2. **Claridad táctil:** controles reconocibles, estados visibles y áreas cómodas.
3. **Jerarquía editorial:** títulos expresivos y datos densos en tipografía funcional.
4. **Calidez contenida:** neutros cálidos, un acento dominante y tonos de celebración secundarios.
5. **Accesibilidad:** contraste AA, teclado completo y significado independiente del color.
6. **Progreso sin juicio:** reconocer constancia y recuperación sin culpa, comparación ni urgencia.

## Tokens

### Color

| Token | Claro | Uso |
| --- | --- | --- |
| `canvas` | `#EFEEE9` | Fondo general piedra cálida |
| `surface` | `#F9F8F4` | Tarjetas, paneles y formularios |
| `surface-raised` | `#FFFFFF` | Superficie elevada puntual |
| `ink` | `#20231F` | Texto principal carbón oliváceo |
| `ink-muted` | `#5F635D` | Texto secundario |
| `line` | `#CBC8BF` | Bordes y divisores |
| `accent` | `#3F4C43` | Acción principal y selección |
| `accent-hover` | `#303A33` | Interacción sobre acento |
| `accent-soft` | `#E1E5DF` | Fondo seleccionado |
| `success` | `#4F6254` | Confirmación y progreso |
| `warning` | `#806A48` | Atención no destructiva |
| `danger` | `#7D4D49` | Error y acción destructiva |
| `focus` | `#315A73` | Anillo de foco de alto contraste |
| `moss` | `#71806D` | Crecimiento y continuidad secundaria |
| `clay-soft` | `#EBE0D2` | Superficie cálida puntual |
| `petal-soft` | `#E8D7CF` | Ornamento y celebraciones suaves |
| `gold-soft` | `#E9D9B8` | Hitos, insignias y recompensas |
| `gold-ink` | `#725A2F` | Texto e icono sobre `gold-soft` |
| `mist` | `#DCE6E0` | Profundidad botánica decorativa |

No usar negro puro ni colores neón. Se permiten lavados radiales muy suaves que combinen tokens
decorativos y no reduzcan contraste; nunca sustituyen una superficie funcional. Los estados
combinan color, forma, iconografía sobria y texto. Un tema oscuro queda fuera de alcance hasta
contar con su propia paleta verificada.

### Tipografía

- **Títulos:** `"Bodoni 72", Didot, "Iowan Old Style", Georgia, serif`.
- **Interfaz y datos:** `"Avenir Next", Inter, system-ui, sans-serif`.
- **Escala fluida:** 14–15, 16–18, 18–20, 24–30, 36–48 y 52–82 px.
- **Cuerpo:** `clamp(18px, 0.3vw + 17px, 20px)`, altura de línea 1.6.
- **Etiquetas:** 16–18 px, peso 600; evitar mayúsculas sostenidas.
- Los títulos usan contraste editorial, peso contenido y espaciado ajustado; nunca sacrifican
  legibilidad por ornamentación.
- **Números financieros:** variantes tabulares cuando estén disponibles.

Las fuentes web son opcionales: la pila local debe conservar jerarquía y rendimiento.

### Espacio y tamaño

La unidad base es 4 px. Escala: 4, 8, 12, 16, 24, 32, 48 y 64 px.

- Contenido principal: ocupa el ancho disponible con máximo de 1480 px y márgenes fluidos.
- Texto largo: máximo 68 caracteres por línea.
- Control interactivo: mínimo 48 × 48 px; navegación principal de al menos 56 px de alto.
- Separación entre secciones: 48 px en escritorio y 32 px en móvil.

### Forma, borde y sombra

- Radios: 6 px para controles, 10 px para tarjetas y 14 px para paneles.
- Borde estándar: 1 px sólido `line`.
- Sombra elevada: `0 8px 24px rgb(38 36 31 / 0.08)`.
- No apilar tarjeta dentro de tarjeta salvo que exista una jerarquía funcional.

## Layout

- Shell con navegación lateral de 260 a 320 px desde 821 px, escalada según el viewport.
- Bajo 821 px, encabezado superior de marca y navegación inferior accesible sin ocultar el destino
  actual.
- El shell usa como mínimo toda la altura dinámica del viewport y evita franjas vacías laterales.
- El contenido y sus márgenes responden de forma fluida al ancho disponible sin desplazamiento
  horizontal.
- Rejilla de 12 columnas en escritorio y una columna en móvil.
- Las páginas comienzan con título, contexto breve y, solo si corresponde, una acción primaria.
- Las métricas se alinean por línea base; no usar mosaicos de tamaños arbitrarios.

## Componentes

### Botón

- Variantes: primario, secundario, texto y destructivo.
- Una sola acción primaria visible por región.
- Etiquetas con verbo específico: “Crear hábito”, no “Aceptar”.
- Carga preserva el ancho, bloquea reenvío y mantiene una etiqueta accesible.

### Campo

- Etiqueta siempre visible sobre el control.
- Ayuda antes del error; error debajo y asociado mediante descripción accesible.
- El placeholder ilustra formato, nunca sustituye la etiqueta.
- Foco con anillo de 2 px y separación de 2 px.

### Tarjeta

- Agrupa información relacionada, no toda sección necesita una tarjeta.
- Encabezado, contenido y acciones siguen el mismo orden visual y del DOM.
- Interactividad solo cuando toda la tarjeta tiene un destino claro y foco visible.

### Estado de hábito

- Pendiente: borde neutro y control vacío.
- Completado: marca, texto explícito y `success`.
- Evitado: marca, texto explícito y `success`; confirma la intención sin registrar recaídas.
- La animación de cambio usa `motion-state` y respeta `prefers-reduced-motion`.

### Datos financieros

- El código o símbolo de moneda acompaña al valor según locale.
- Valores negativos incluyen signo y texto contextual.
- Las cifras de demostración llevan una etiqueta persistente, no solo un aviso temporal.

### Gamificación

- XP, nivel e insignias son información secundaria; nunca desplazan la tarea principal.
- Los desafíos muestran objetivo, progreso, periodo y estado sin cuenta regresiva alarmista.
- Las recompensas personales usan el nombre escrito por el usuario y no simulan valor monetario.
- Una racha interrumpida ofrece continuidad o recuperación con texto neutral; no usa pérdida visual,
  colores destructivos ni mensajes de culpa.
- El check-in confirmado puede usar una celebración local; nivel, insignia, desafío y recompensa
  alcanzados pueden usar una celebración de hito. Duran como máximo 600 ms, pueden descartarse y no
  bloquean navegación ni entrada.
- Con `prefers-reduced-motion`, la celebración es una confirmación estática sin confeti,
  desplazamiento ni transformación.

## Iconografía e imágenes

Usar iconos lineales de 18–20 px con trazo consistente. Cada icono de acción requiere nombre
accesible. Se permiten motivos SVG botánicos abstractos y texturas minerales sin información,
ocultos a tecnologías de asistencia y separados de controles. No usar emojis, fotografías de stock
ni iconos rellenos de estilos mezclados.

## Voz y contenido

- Español claro, directo y respetuoso.
- Frases breves y verbos concretos.
- Evitar tono moralizante: usar “Pendiente”, no “Fallaste”.
- Evitar presión o vergüenza: usar “Puedes continuar hoy”, no “Perdiste tu progreso”.
- No atribuir virtud, disciplina, salud ni responsabilidad financiera a puntos, rachas o saldos.
- Explicar cómo recuperarse de un error.
- Fechas legibles en UI y formato ISO en contratos.

## Movimiento

| Token | Duración | Uso |
| --- | ---: | --- |
| `motion-instant` | 80 ms | Presión y respuesta táctil |
| `motion-state` | 160 ms | Estado, hover, foco y check-in |
| `motion-emphasis` | 320 ms | Progreso y entrada de feedback |
| `motion-celebration` | 600 ms | Secuencia de hito no bloqueante |

- Usar una curva de salida rápida para entradas y estado; la respuesta comienza de inmediato.
- Animar opacidad y transformación; evitar animar layout, desenfoque grande o dimensiones.
- Una microrespuesta permanece en el componente que originó la acción.
- Una celebración combina como máximo tres capas: superficie, símbolo y partículas orgánicas.
- Las partículas son abstractas, finitas y locales; nunca simulan moneda, premio aleatorio o
  actividad social.
- No usar rebote repetitivo, parallax, giro continuo, destello, estrobo ni movimiento automático.
- Con movimiento reducido, sustituir desplazamiento, escala y partículas por cambio estático de
  borde, color, símbolo y texto.

## Estados y accesibilidad

Todo componente interactivo define: reposo, hover, foco, activo, deshabilitado, carga y error
cuando aplique. El orden de foco sigue el visual, los diálogos restauran foco y los mensajes
dinámicos importantes se anuncian. Objetivo WCAG 2.2 AA.

## Criterios de aceptación visual

- Las pantallas usan exclusivamente tokens documentados o una decisión registrada.
- Existe un solo acento principal y una acción primaria por región.
- Texto normal y controles alcanzan contraste AA.
- El layout funciona a 320, 768, 1024 y 1440 px.
- Teclado y foco permiten completar todos los flujos.
- La interfaz sigue siendo comprensible en escala de grises.
- `prefers-reduced-motion` elimina el movimiento no esencial.
- La tipografía, navegación y espaciado escalan sin saltos entre 320 y 1440 px.
- La marca, los destinos principales y el destino activo siguen siendo legibles en todos los
  tamaños soportados.
- Una celebración no bloquea la acción siguiente, puede descartarse y tiene alternativa estática.
- Rachas, XP, insignias y finanzas usan lenguaje neutral y siguen siendo comprensibles sin color.
- No aparecen negro puro, emojis, neón ni patrones de panel genérico; los lavados decorativos
  conservan contraste y no comunican estado.

## Decisiones registradas

- **D-DS-01:** combinar serif editorial en títulos con sans serif funcional.
- **D-DS-02:** adoptar neutros minerales y verde carbón como base visual.
- **D-DS-03:** usar bordes antes que sombras para expresar agrupación.
- **D-DS-04:** no ofrecer tema oscuro en la primera etapa.
- **D-DS-05:** mantener el movimiento breve, funcional y reducible.
- **D-DS-06:** permitir celebraciones puntuales de hasta 600 ms solo para logros explícitos, con
  alternativa estática y sin interrupción del flujo.
- **D-DS-07:** presentar la gamificación como contexto secundario y privado, sin señales de pérdida,
  comparación social o juicio personal.
- **D-DS-08:** adoptar una jerarquía editorial fluida con serif de alto contraste, cuerpo mínimo de
  17 px y navegación ampliada para mejorar legibilidad y presencia visual.
- **D-DS-09:** hacer que el shell ocupe el viewport disponible, con barra lateral fluida en
  escritorio y encabezado de marca más navegación inferior en móvil.
- **D-DS-10:** refinar la paleta hacia piedra cálida, carbón oliváceo y verde profundo para una
  presencia más sobria, reduciendo la saturación de superficies, selección y estados.
- **D-DS-11:** evolucionar la dirección hacia una presencia orgánica y celebratoria mediante tonos
  secundarios, motivos botánicos abstractos y profundidad mineral, sin competir con la tarea.
- **D-DS-12:** adoptar cuatro tokens de duración y limitar cada celebración a tres capas finitas,
  activadas solo por una acción confirmada.
- **D-DS-13:** permitir lavados radiales decorativos de bajo contraste, pero no degradados como
  superficie funcional ni como portadores de significado.
