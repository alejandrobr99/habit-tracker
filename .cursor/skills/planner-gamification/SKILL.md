---
name: planner-gamification
description: Diseña, implementa y revisa gamificación privada y no moralizante para el planificador. Se usa automáticamente al trabajar con XP, niveles, insignias, desafíos semanales, recompensas, canjes, rachas, recuperación, celebraciones o motivación en hábitos y finanzas.
---

# Gamificación del planificador

## Fuente de verdad

Lee primero `specs/003-gamification.md` y la especificación del dominio afectado:
`specs/001-habit-tracker.md` o `specs/004-finance-mvp.md`. Consulta `specs/design-system.md`
si cambia la interfaz, [RESEARCH.md](RESEARCH.md) si se evalúa una mecánica o tono y activa
`planner-visual-delight/SKILL.md` solo para movimiento, celebración u ornamentación.

Si falta un comportamiento, actualiza primero la especificación. No inventes eventos, cantidades de
XP, insignias, estados ni señales financieras en código.

## Principios

- Apoya autonomía: el usuario elige hábito, desafío y recompensa; la función principal no depende
  de participar en gamificación.
- Refuerza competencia: muestra progreso comprensible, criterios estables y recuperación posible.
- No simula relatedness: sin comunidad real, no inventa avatares, rivales, actividad social ni
  aprobación ficticia.
- Trata engagement como una métrica de interacción, no como prueba de eficacia o bienestar.
- Mantén la gamificación privada y separada de notas, importes y contenido sensible.
- Nunca uses culpa, vergüenza, escasez artificial, urgencia artificial, pérdida automática o
  comparación. Un costo voluntario solo es válido si se muestra antes de confirmar.

## Reglas de dominio

- Todo XP procede del catálogo especificado y entra por un ledger idempotente.
- Ninguna mutación pública crea XP o insignias directamente.
- El nivel usa XP positivo de por vida; los canjes solo reducen XP disponible.
- Un desafío expirado termina sin penalización ni mensaje de fracaso.
- Una recuperación de ayer conserva continuidad, no genera XP positivo, desafío o insignia y
  debita exactamente el costo especificado de forma atómica e idempotente.
- Finanzas solo genera reconocimiento por el primer presupuesto y la revisión semanal.
- Nunca uses monto, saldo, ahorro, gasto o cantidad de movimientos como mérito.
- Las recompensas las define el usuario; no prometen valor externo ni resultado conductual.

## Flujo de trabajo

1. Enumera los criterios de aceptación aplicables y los eventos origen.
2. Define la clave idempotente antes de escribir una mutación.
3. Separa hechos de dominio, proyecciones calculadas y presentación.
4. Modela camino feliz, repetición, conflicto, reversión y concurrencia.
5. Revisa privacidad: el ledger no debe copiar nombres, notas ni importes.
6. Diseña carga, vacío, progreso, logro, expiración, insuficiencia, recuperación y error.
7. Aplica el sistema visual y la voz neutral.
8. Prueba reglas y contratos en proporción al riesgo.

## Diseño de interfaz

- En Hoy, usa nivel, XP y racha como contexto principal para orientar pendientes; en las demás
  pantallas mantenlos subordinados a la tarea del dominio.
- Explica barras con texto y cifras; no dependas de color.
- No uses cuentas regresivas alarmistas ni estados destructivos para una racha.
- Delega la coreografía y alternativa de movimiento a `planner-visual-delight`.
- Después de una ausencia, ofrece “Continuar hoy” aunque la recuperación no esté disponible.
- Usa “La semana terminó” y “XP disponible”; evita “Fallaste” o “Necesitas esforzarte”.

## Verificación

- El mismo evento procesado dos veces produce una entrada y un efecto.
- Un canje repetido o concurrente no cobra dos veces ni deja saldo negativo.
- Eliminar y recrear un check-in conserva el reconocimiento histórico sin duplicar XP.
- Recuperar ayer afecta la racha y el XP disponible exactamente una vez, sin reducir XP histórico
  ni nivel.
- Expirar un desafío no resta progreso acumulado.
- Finanzas no emite eventos por importes, saldos o movimientos.
- El UI funciona con teclado, foco visible, escala de grises y movimiento reducido.
- Logs, analítica y respuestas no filtran datos privados.
