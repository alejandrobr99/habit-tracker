# Configuración segura del OCR financiero con Gemini

Esta configuración envía temporalmente el documento financiero al backend de Google Gemini
para proponer movimientos. No es OCR local. La aplicación elimina su copia temporal al terminar,
pero eso no significa que el proveedor la destruya inmediatamente.

## Modelo y coste

El modelo configurado es `gemini-3.1-flash-lite`, porque admite imágenes, PDF y salidas estructuradas
y está orientado a extracción sencilla de bajo coste. Al 12 de agosto de 2026, la página oficial de
precios mostraba USD 0.25 por millón de tokens de entrada y USD 1.50 por millón de tokens de salida
en el nivel pagado. Verifica el precio vigente antes de activar el módulo: el backend no debe
considerar una tarifa antigua como garantía.

La aplicación usa dos barreras:

1. El proyecto de Google usa créditos prepagados por USD 10.
2. La aplicación conserva un presupuesto máximo de USD 10 y reserva el coste máximo antes de llamar.

La barrera interna no sustituye al proveedor. Google descuenta el prepago casi en tiempo real y
detiene los servicios cuando el saldo llega a cero, pero advierte que la latencia de medición puede
dejar un saldo ligeramente negativo. No actives recarga automática.

## Crear el proyecto de prueba

1. Crea un proyecto separado en Google AI Studio o Google Cloud solo para este experimento.
2. Habilita la Gemini API para ese proyecto.
3. Abre la sección de facturación de AI Studio.
4. Elige el plan pagado prepagado, si está disponible para tu cuenta.
5. Compra manualmente USD 10 de créditos.
6. Deja **Auto-reload** desactivado. No registres una recarga automática.
7. Revisa que el saldo disponible sea USD 10 y que ningún otro proyecto use esa cuenta prepagada.
8. Configura una alerta de facturación de bajo umbral. La alerta informa, pero no sustituye el corte.

El prepago puede expirar según las condiciones vigentes y no necesariamente es reembolsable. Para
una prueba, considera esos USD 10 como gasto máximo planificado, no como saldo recuperable.

## Crear y restringir la clave

1. Crea una clave dedicada a este proyecto y a este entorno.
2. No reutilices una clave personal ni una clave usada por el frontend.
3. En las restricciones de API permite solo `generativelanguage.googleapis.com`.
4. En Railway aplica una restricción por IP solo si tienes una IP de salida fija verificable. Si no
   existe, conserva como mínimo la restricción de API y la clave únicamente en el backend.
5. Copia la clave una sola vez al gestor de secretos. No la pegues en una issue, chat, captura,
   repositorio o archivo `.env` versionado.
6. Si sospechas una filtración, revoca la clave inmediatamente, crea otra y revisa el consumo.

La clave no se configura en `VITE_*`: esas variables terminan en el navegador. El navegador solo
llama al backend autenticado.

## Configuración local

Copia `backend/environment.example` a `backend/.env` y añade:

```dotenv
GEMINI_API_KEY=pon_aqui_la_clave_sin_comillas
PLANNER_OCR_ENABLED=true
PLANNER_OCR_BUDGET_MICROUSD=10000000
PLANNER_OCR_MAX_CALLS_PER_HOUR=20
```

No uses una imagen o extracto real para la primera prueba. Usa un documento sintético que no contenga
nombre, dirección, número de cuenta, tarjeta ni identificadores fiscales.

## Configuración en Railway

En **Variables** del servicio configura la clave como secreto:

```text
GEMINI_API_KEY=<valor secreto>
PLANNER_OCR_ENABLED=true
PLANNER_OCR_BUDGET_MICROUSD=10000000
PLANNER_OCR_MAX_CALLS_PER_HOUR=20
```

No añadas la clave a `railpack.json`, `railway.json`, `README.md` ni a variables `VITE_`. Mantén una
sola réplica porque la aplicación usa SQLite y el presupuesto interno es persistente en esa base.
Antes de desplegar, crea un snapshot del volumen.

Para apagar el OCR, establece `PLANNER_OCR_ENABLED=false` o elimina `GEMINI_API_KEY` y despliega.
La interfaz debe mostrar que la función no está configurada; no debe intentar otro proveedor.

## Datos sensibles y retención

El nivel pagado de Gemini no usa prompts, archivos ni respuestas para mejorar sus productos, según
los términos actuales del servicio. Google puede conservar temporalmente esos datos para detectar
abuso, seguridad u obligaciones legales. Por ello:

- no subas documentos que no aceptarías procesar en un proveedor externo;
- informa a la persona antes de analizar;
- usa datos sintéticos para pruebas automatizadas;
- no utilices la cuota gratuita para documentos financieros;
- no envíes el documento mediante Files API, URLs públicas, grounding o caché;
- elimina la copia temporal local después de cada análisis;
- no guardes prompt, respuesta, texto extraído, nombre de archivo o contenido en logs.

## Contención del gasto

La aplicación rechaza nuevos análisis cuando el presupuesto interno se agota y limita a 20 análisis
por usuario cada hora, configurable mediante `PLANNER_OCR_MAX_CALLS_PER_HOUR`. El presupuesto y el
límite horario son controles diferentes y la interfaz muestra mensajes distintos. No hay reintentos
automáticos. Los fallos antes de llamar al proveedor no consumen presupuesto. Ante una respuesta de
red incierta se conserva la reserva para evitar volver a gastar sin saber si la primera llamada tuvo
éxito.

Comprueba periódicamente:

- saldo prepagado en AI Studio;
- consumo por proyecto y por clave;
- presupuesto usado y restante en `/api/v1/finance/imports/budget`;
- alertas de facturación;
- logs de seguridad, que deben contener solo estado y metadatos acotados.

## Cierre de la prueba

1. Desactiva `PLANNER_OCR_ENABLED`.
2. Revoca y elimina la clave dedicada.
3. Elimina el proyecto de prueba cuando ya no necesites su historial.
4. Confirma que no quedan archivos temporales en el volumen.
5. Conserva únicamente la documentación y fixtures sintéticos.

La API oficial puede cambiar precios, nombres de modelos, límites o condiciones. Revisa antes de
cada despliegue:

- [Modelo Gemini 3.1 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite)
- [Precios](https://ai.google.dev/gemini-api/docs/pricing)
- [Facturación prepagada](https://ai.google.dev/gemini-api/docs/billing)
- [Claves y restricciones](https://ai.google.dev/gemini-api/docs/api-key)
- [Términos de Gemini API](https://ai.google.dev/gemini-api/terms)

