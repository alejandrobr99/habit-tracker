import type { HabitWeeklySummary } from "../types/planner";

export type SpectacleKind = "day" | "streak" | "target";

export interface SpectacleMoment {
  description: string;
  eyebrow: string;
  kind: SpectacleKind;
  title: string;
  unit: string;
  value: number;
}

interface SelectSpectacleInput {
  after: HabitWeeklySummary;
  before: HabitWeeklySummary;
  date: string;
  summaries: HabitWeeklySummary[];
  todayKey: string;
}

const STREAK_MILESTONES = new Set([3, 7, 14, 30]);

function isStreakMilestone(value: number): boolean {
  return STREAK_MILESTONES.has(value) || (value > 30 && value % 30 === 0);
}

export function selectCheckInSpectacle({
  after,
  before,
  date,
  summaries,
  todayKey,
}: SelectSpectacleInput): SpectacleMoment | null {
  const completedToday = date === todayKey
    && summaries.length > 0
    && summaries.every((summary) => summary.check_in_dates.includes(todayKey));

  if (completedToday) {
    return {
      description: "Todas las intenciones activas de hoy quedaron registradas.",
      eyebrow: "Día completo",
      kind: "day",
      title: "Tu día floreció",
      unit: summaries.length === 1 ? "hábito" : "hábitos",
      value: summaries.length,
    };
  }

  const reachedWeeklyTarget = before.completed_count < before.target_count
    && after.completed_count >= after.target_count;
  if (reachedWeeklyTarget) {
    return {
      description: `${after.habit.name} alcanzó la meta que elegiste para esta semana.`,
      eyebrow: "Meta semanal",
      kind: "target",
      title: "El ritmo está completo",
      unit: after.target_count === 1 ? "avance" : "avances",
      value: after.target_count,
    };
  }

  const reachedStreak = after.current_streak !== before.current_streak
    && isStreakMilestone(after.current_streak);
  if (reachedStreak) {
    return {
      description: `${after.habit.name} continúa creciendo a tu ritmo.`,
      eyebrow: "Hito de racha",
      kind: "streak",
      title: "Una continuidad que se siente",
      unit: after.habit.frequency === "daily" ? "días" : "semanas",
      value: after.current_streak,
    };
  }

  return null;
}
