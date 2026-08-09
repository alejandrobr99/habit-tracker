# Constitución de desarrollo

Este documento define los principios que prevalecen cuando una especificación no alcanza para
resolver una decisión técnica. Cambiar un principio requiere una decisión explícita y documentada.

## 1. La sencillez es una restricción

- Elegir la solución correcta más simple que cubra el comportamiento especificado.
- No construir abstracciones para una segunda implementación hipotética.
- Preferir código explícito y repetido de forma limitada antes que una abstracción difícil de leer.
- Extraer una abstracción cuando exista repetición estable, no solo similitud superficial.
- No añadir colas, cachés, microservicios, repositorios genéricos ni capas de compatibilidad sin
  evidencia medible que los justifique.

## 2. Robustez proporcional

- Validar datos en los límites: entrada HTTP, configuración y persistencia.
- Modelar explícitamente errores y estados recuperables que el producto ya necesita.
- Cubrir con pruebas las reglas de dominio, contratos HTTP y recorridos críticos de interfaz.
- No simular robustez con reintentos, tolerancia distribuida o manejo de casos imposibles para el
  despliegue actual.

## 3. Parametrización con propósito

- Parametrizar valores que cambian entre entornos o instalaciones: URL de base de datos, orígenes
  permitidos, prefijo de API y URL pública del backend.
- Mantener como código versionado las reglas de producto, tokens de diseño y decisiones de dominio.
- Cada parámetro debe tener nombre, valor local seguro, validación y documentación.
- No convertir constantes internas en configuración sin un caso real de variación.

## 4. Desarrollo guiado por especificaciones

- Toda función comienza con criterios de aceptación observables.
- El contrato implementado y las pruebas deben usar los mismos nombres y formas descritos en la
  especificación.
- Una discrepancia entre spec, frontend y backend es un defecto, no una decisión implícita.
- Las decisiones duraderas se registran cerca de la especificación afectada.

## 5. Calidad automatizada

- Backend: `uv` para entorno y bloqueo, Ruff para formato y lint, pytest para pruebas y cobertura.
- Frontend: npm con lockfile, TypeScript estricto, Oxlint, Vitest y Testing Library.
- La integración continua ejecuta formato, lint, tipos, pruebas y builds reproducibles.
- Una prueba debe verificar comportamiento público; se evitan tests acoplados a detalles internos.
- Los casos críticos incluyen camino feliz, validación, ausencia, conflicto e idempotencia.

## 6. Diseño sereno y accesible

- La interfaz reduce decisiones, ruido y ornamentación antes de agregar componentes.
- Los tokens son la única fuente para color, tipografía, espaciado, radios y movimiento compartidos.
- Toda acción funciona con teclado, foco visible, contraste suficiente y texto comprensible.
- La personalización se logra cambiando tokens y configuración estable, no duplicando pantallas.

## 7. Optimización basada en evidencia

- Primero se mide, luego se optimiza.
- SQLite, consultas directas y renderizado cliente son suficientes mientras las métricas reales no
  demuestren lo contrario.
- Se acepta más código local cuando hace el flujo más fácil de entender, probar y cambiar.
- El rendimiento no justifica ocultar reglas de negocio detrás de abstracciones prematuras.

## Lista de decisión

Antes de añadir una dependencia, capa o parámetro:

1. ¿Resuelve un criterio de aceptación actual?
2. ¿La alternativa directa es insuficiente de forma demostrable?
3. ¿Reduce el costo total de entender, probar y operar el sistema?
4. ¿Se puede retirar sin migraciones complejas?

Si las respuestas no son claras, se elige la solución directa y se registra la necesidad pendiente.
