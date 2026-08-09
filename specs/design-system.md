# Sistema de diseño

## Dirección

La interfaz debe sentirse sobria, elegante y cercana: una herramienta personal que acompaña sin
competir por atención. La calidez procede de fondos minerales, tipografía cuidada y acentos
terrosos, no de decoración nostálgica. Se evita la estética genérica de panel SaaS.

## Principios

1. **Serenidad:** pocos niveles simultáneos, aire suficiente y movimiento mínimo.
2. **Claridad táctil:** controles reconocibles, estados visibles y áreas cómodas.
3. **Jerarquía editorial:** títulos expresivos y datos densos en tipografía funcional.
4. **Calidez contenida:** neutros cálidos con un único acento dominante.
5. **Accesibilidad:** contraste AA, teclado completo y significado independiente del color.
6. **Progreso sin juicio:** reconocer constancia y recuperación sin culpa, comparación ni urgencia.

## Tokens

### Color

| Token | Claro | Uso |
| --- | --- | --- |
| `canvas` | `#F5F1E8` | Fondo general marfil mineral |
| `surface` | `#FCFAF5` | Tarjetas, paneles y formularios |
| `surface-raised` | `#FFFFFF` | Superficie elevada puntual |
| `ink` | `#26241F` | Texto principal |
| `ink-muted` | `#6E695F` | Texto secundario |
| `line` | `#D9D2C5` | Bordes y divisores |
| `accent` | `#7A5C3E` | Acción principal y selección |
| `accent-hover` | `#62482F` | Interacción sobre acento |
| `accent-soft` | `#E9DED0` | Fondo seleccionado |
| `success` | `#536B57` | Confirmación y progreso |
| `warning` | `#956F35` | Atención no destructiva |
| `danger` | `#934E45` | Error y acción destructiva |
| `focus` | `#315C7A` | Anillo de foco de alto contraste |

No usar negro puro, degradados ni colores neón. Los estados combinan color, iconografía sobria y
texto. Un tema oscuro queda fuera de alcance hasta contar con su propia paleta verificada.

### Tipografía

- **Títulos:** `"Bodoni 72", Didot, "Iowan Old Style", Georgia, serif`.
- **Interfaz y datos:** `"Avenir Next", Inter, system-ui, sans-serif`.
- **Escala fluida:** 13–14, 15–17, 17–19, 22–28, 32–44 y 48–76 px.
- **Cuerpo:** `clamp(17px, 0.3vw + 16px, 19px)`, altura de línea 1.6.
- **Etiquetas:** 15–17 px, peso 600; evitar mayúsculas sostenidas.
- Los títulos usan contraste editorial, peso contenido y espaciado ajustado; nunca sacrifican
  legibilidad por ornamentación.
- **Números financieros:** variantes tabulares cuando estén disponibles.

Las fuentes web son opcionales: la pila local debe conservar jerarquía y rendimiento.

### Espacio y tamaño

La unidad base es 4 px. Escala: 4, 8, 12, 16, 24, 32, 48 y 64 px.

- Contenido principal: ocupa el ancho disponible con máximo de 1480 px y márgenes fluidos.
- Texto largo: máximo 68 caracteres por línea.
- Control interactivo: mínimo 44 × 44 px.
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
- Omitido: trazo breve, etiqueta “Omitido” y tono neutral.
- La animación de cambio dura 140–180 ms y respeta `prefers-reduced-motion`.

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
- Las celebraciones se reservan para nivel, insignia, desafío o recompensa alcanzados. Duran como
  máximo 600 ms, pueden descartarse y no bloquean navegación ni entrada.
- Con `prefers-reduced-motion`, la celebración es una confirmación estática sin confeti,
  desplazamiento ni transformación.

## Iconografía e imágenes

Usar iconos lineales de 18–20 px con trazo consistente. Cada icono de acción requiere nombre
accesible. No usar ilustraciones decorativas, emojis, fotografías de stock ni iconos rellenos de
estilos mezclados.

## Voz y contenido

- Español claro, directo y respetuoso.
- Frases breves y verbos concretos.
- Evitar tono moralizante: usar “Pendiente”, no “Fallaste”.
- Evitar presión o vergüenza: usar “Puedes continuar hoy”, no “Perdiste tu progreso”.
- No atribuir virtud, disciplina, salud ni responsabilidad financiera a puntos, rachas o saldos.
- Explicar cómo recuperarse de un error.
- Fechas legibles en UI y formato ISO en contratos.

## Movimiento

- Transiciones funcionales entre 120 y 220 ms.
- Animar opacidad y transformación; evitar animar layout.
- Las celebraciones permitidas son breves, no repetitivas y nunca usan rebotes ni movimiento
  continuo.
- Con movimiento reducido, eliminar transiciones no esenciales.

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
- No aparecen degradados, negro puro, emojis ni patrones de panel genérico.

## Decisiones registradas

- **D-DS-01:** combinar serif editorial en títulos con sans serif funcional.
- **D-DS-02:** adoptar marfil mineral y marrón terroso como base visual.
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
