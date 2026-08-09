import { ArrowRight, Check, Flame, Leaf, Target } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Celebration } from "../components/ui/Celebration";
import { OrganicMotif } from "../components/ui/OrganicMotif";
import { StatusPanel } from "../components/ui/StatusPanel";
import { plannerApi } from "../lib/api";
import { formatLongDate, startOfWeek, toDateKey } from "../lib/date";

export function TodayPage() {
  const [celebratedHabit, setCelebratedHabit] = useState<{
    id: number;
    name: string;
  } | null>(null);
  const today = new Date();
  const todayKey = toDateKey(today);
  const weekKey = toDateKey(startOfWeek(today));
  const queryClient = useQueryClient();
  const habitsQuery = useQuery({
    queryKey: ["habits"],
    queryFn: plannerApi.listHabits,
  });
  const summaryQuery = useQuery({
    queryKey: ["weekly-summary", weekKey],
    queryFn: () => plannerApi.getWeeklySummary(weekKey),
  });
  const checkInMutation = useMutation({
    mutationFn: async ({
      checked,
      habitId,
    }: {
      checked: boolean;
      habitId: number;
    }) => {
      if (checked) {
        await plannerApi.removeCheckIn(habitId, todayKey);
      } else {
        await plannerApi.checkIn(habitId, todayKey);
      }
    },
    onSuccess: async (_, variables) => {
      if (variables.checked) {
        setCelebratedHabit(null);
      } else {
        const habit = habitsQuery.data?.find(
          (item) => item.id === variables.habitId,
        );
        if (habit) {
          setCelebratedHabit({ id: habit.id, name: habit.name });
        }
      }
      await queryClient.invalidateQueries({ queryKey: ["weekly-summary"] });
    },
  });

  const habits =
    habitsQuery.data?.filter((habit) => habit.status === "active") ?? [];
  const summaries = new Map(
    summaryQuery.data?.habits.map((summary) => [
      summary.habit.id,
      summary,
    ]) ?? [],
  );
  const doneToday = habits.filter((habit) =>
    summaries.get(habit.id)?.check_in_dates.includes(todayKey),
  ).length;
  const activeStreaks = [...summaries.values()].filter(
    (summary) => summary.current_streak > 0,
  ).length;
  const progress = habits.length === 0 ? 0 : (doneToday / habits.length) * 100;
  const completedThisWeek = [...summaries.values()].reduce(
    (total, summary) => total + summary.completed_count,
    0,
  );
  const weeklyTarget = [...summaries.values()].reduce(
    (total, summary) => total + summary.target_count,
    0,
  );
  const weeklyProgress =
    weeklyTarget === 0 ? 0 : (completedThisWeek / weeklyTarget) * 100;

  return (
    <div className="page">
      <header className="today-header">
        <div className="today-hero-copy">
          <span className="eyebrow">{formatLongDate(today)}</span>
          <h1>Un día a la vez.</h1>
          <p>
            Cada registro hace visible el ritmo que elegiste construir.
          </p>
        </div>
        <OrganicMotif className="hero-motif" variant="sprout" />
        <div className="daily-orb">
          <div
            aria-label={`${doneToday} de ${habits.length} hábitos completados`}
            className="progress-ring"
          >
            <svg aria-hidden="true" viewBox="0 0 44 44">
              <circle cx="22" cy="22" r="18" />
              <circle
                cx="22"
                cy="22"
                r="18"
                style={{ strokeDashoffset: 113 - (113 * progress) / 100 }}
              />
            </svg>
          </div>
          <div className="daily-orb__copy">
            <strong>{Math.round(progress)}%</strong>
            <span>hoy</span>
          </div>
        </div>
      </header>

      <section aria-label="Resumen del día" className="summary-cards">
        <article className="summary-card">
          <span className="summary-card__icon summary-card__icon--sage">
            <Target aria-hidden="true" size={19} />
          </span>
          <div>
            <strong>{doneToday}/{habits.length}</strong>
            <span>hábitos de hoy</span>
          </div>
        </article>
        <article className="summary-card">
          <span className="summary-card__icon summary-card__icon--clay">
            <Flame aria-hidden="true" size={19} />
          </span>
          <div>
            <strong>{activeStreaks}</strong>
            <span>rachas activas</span>
          </div>
        </article>
        <article className="summary-card">
          <span className="summary-card__icon summary-card__icon--gold">
            <Leaf aria-hidden="true" size={19} />
          </span>
          <div>
            <strong>{Math.round(weeklyProgress)}%</strong>
            <span>ritmo semanal</span>
          </div>
        </article>
      </section>

      {celebratedHabit && (
        <Celebration
          description="Tu progreso de hoy ya refleja este avance."
          kind="check-in"
          onDismiss={() => setCelebratedHabit(null)}
          title={`${celebratedHabit.name} quedó completado`}
        />
      )}

      <section className="today-section">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Para hoy</span>
            <h2>Tu lista breve</h2>
          </div>
          <Link className="inline-link" to="/habitos">
            Ver semana
            <ArrowRight aria-hidden="true" size={16} />
          </Link>
        </div>

        {habitsQuery.isLoading || summaryQuery.isLoading ? (
          <StatusPanel
            description="Organizando tus prioridades."
            kind="loading"
            title="Preparando tu día"
          />
        ) : habitsQuery.isError || summaryQuery.isError ? (
          <StatusPanel
            action={
              <Button
                onClick={() => {
                  void habitsQuery.refetch();
                  void summaryQuery.refetch();
                }}
                variant="secondary"
              >
                Reintentar
              </Button>
            }
            description="No pudimos conectar con tu agenda."
            kind="error"
            title="Tu resumen no está disponible"
          />
        ) : habits.length === 0 ? (
          <StatusPanel
            action={
              <Link className="button button--primary" to="/habitos">
                Crear un hábito
              </Link>
            }
            description="Crea tu primer hábito para empezar a registrar avances."
            kind="empty"
            title="Tu día está despejado"
          />
        ) : (
          <div className="today-list">
            {habits.map((habit) => {
              const checked =
                summaries
                  .get(habit.id)
                  ?.check_in_dates.includes(todayKey) ?? false;
              const streak = summaries.get(habit.id)?.current_streak ?? 0;
              return (
                <article
                  className="today-habit"
                  data-celebrating={celebratedHabit?.id === habit.id}
                  data-complete={checked}
                  key={habit.id}
                >
                  <button
                    aria-label={`${
                      habit.direction === "avoid"
                        ? checked
                          ? "Desmarcar evitado"
                          : "Marcar como evitado"
                        : checked
                          ? "Desmarcar"
                          : "Marcar"
                    } ${habit.name}`}
                    aria-pressed={checked}
                    className={`today-check${checked ? " today-check--checked" : ""}`}
                    disabled={checkInMutation.isPending}
                    onClick={() =>
                      checkInMutation.mutate({
                        checked,
                        habitId: habit.id,
                      })
                    }
                    style={
                      checked ? { backgroundColor: habit.color } : undefined
                    }
                    type="button"
                  >
                    {checked && <Check aria-hidden="true" size={18} />}
                  </button>
                  <span
                    aria-hidden="true"
                    className="habit-color"
                    style={{ backgroundColor: habit.color }}
                  />
                  <div>
                    <h3>{habit.name}</h3>
                    <p>
                      <span className="habit-state">
                        {checked
                          ? habit.direction === "avoid"
                            ? "Evitado"
                            : "Completado"
                          : "Pendiente"}
                      </span>
                      {!checked && (
                        <>
                          {" · "}
                          {habit.description
                            || (habit.frequency === "daily"
                              ? "Cada día"
                              : "Una vez por semana")}
                        </>
                      )}
                    </p>
                  </div>
                  <span className="today-habit__streak">
                    <Flame aria-hidden="true" size={15} />
                    {streak}
                  </span>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
