import {
  Archive,
  Check,
  ChevronLeft,
  ChevronRight,
  Flame,
  MoreHorizontal,
  Pencil,
  Plus,
  RotateCcw,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { StatusPanel } from "../components/ui/StatusPanel";
import { HabitDialog } from "../features/habits/HabitDialog";
import { ApiError, plannerApi } from "../lib/api";
import {
  formatShortDate,
  formatShortDay,
  getWeekDays,
  startOfWeek,
  toDateKey,
} from "../lib/date";
import type { HabitInput } from "../types/planner";

export function HabitsPage() {
  const [week, setWeek] = useState(() => startOfWeek());
  const [recoveryMessage, setRecoveryMessage] = useState<{
    habitId: number;
    kind: "error" | "success";
    text: string;
  } | null>(null);
  const queryClient = useQueryClient();
  const weekKey = toDateKey(week);
  const weekDays = getWeekDays(week);
  const todayKey = toDateKey(new Date());
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayKey = toDateKey(yesterday);

  const habitsQuery = useQuery({
    queryKey: ["habits"],
    queryFn: plannerApi.listHabits,
  });
  const summaryQuery = useQuery({
    queryKey: ["weekly-summary", weekKey],
    queryFn: () => plannerApi.getWeeklySummary(weekKey),
  });

  const saveMutation = useMutation({
    mutationFn: ({
      habitId,
      input,
    }: {
      habitId?: number;
      input: HabitInput;
    }) =>
      habitId
        ? plannerApi.updateHabit(habitId, input)
        : plannerApi.createHabit(input),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["habits"] }),
        queryClient.invalidateQueries({ queryKey: ["weekly-summary"] }),
      ]);
    },
  });

  const archiveMutation = useMutation({
    mutationFn: plannerApi.archiveHabit,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["habits"] }),
        queryClient.invalidateQueries({ queryKey: ["weekly-summary"] }),
      ]);
    },
  });

  const checkInMutation = useMutation({
    mutationFn: async ({
      checked,
      date,
      habitId,
    }: {
      checked: boolean;
      date: string;
      habitId: number;
    }) => {
      if (checked) {
        await plannerApi.removeCheckIn(habitId, date);
      } else {
        await plannerApi.checkIn(habitId, date);
      }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["weekly-summary"] });
    },
  });

  const recoveryMutation = useMutation({
    mutationFn: (habitId: number) =>
      plannerApi.createStreakRecovery(habitId, yesterdayKey),
    onSuccess: async (_, habitId) => {
      setRecoveryMessage({
        habitId,
        kind: "success",
        text: "Ayer quedó recuperado para la continuidad de tu racha.",
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["weekly-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["progress"] }),
        queryClient.invalidateQueries({ queryKey: ["badges"] }),
      ]);
    },
    onError: (error, habitId) => {
      const recoverable = error instanceof ApiError
        && (error.status === 409 || error.status === 422);
      setRecoveryMessage({
        habitId,
        kind: "error",
        text: recoverable
          ? "Ayer no está disponible para recuperación. Puedes continuar con el registro de hoy."
          : "No pudimos recuperar ayer. Inténtalo nuevamente.",
      });
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

  function moveWeek(direction: number) {
    setWeek((current) => {
      const next = new Date(current);
      next.setDate(current.getDate() + direction * 7);
      return next;
    });
  }

  async function saveHabit(input: HabitInput, habitId?: number) {
    await saveMutation.mutateAsync({ habitId, input });
  }

  if (habitsQuery.isLoading || summaryQuery.isLoading) {
    return (
      <PageFrame>
        <StatusPanel
          description="Estamos preparando tu semana."
          kind="loading"
          title="Cargando hábitos"
        />
      </PageFrame>
    );
  }

  if (habitsQuery.isError || summaryQuery.isError) {
    return (
      <PageFrame>
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
          description="Revisa que la API esté disponible e inténtalo de nuevo."
          kind="error"
          title="No pudimos cargar tus hábitos"
        />
      </PageFrame>
    );
  }

  return (
    <PageFrame>
      <header className="page-header">
        <div>
          <span className="eyebrow">Ritmos y constancia</span>
          <h1>Hábitos</h1>
          <p>Avanza con pequeños registros, sin perseguir la perfección.</p>
        </div>
        <HabitDialog
          isPending={saveMutation.isPending}
          onSave={(input) => saveHabit(input)}
        >
          <Button>
            <Plus aria-hidden="true" size={18} />
            Nuevo hábito
          </Button>
        </HabitDialog>
      </header>

      <section aria-label="Selector de semana" className="week-toolbar">
        <div>
          <span>Semana</span>
          <strong>
            {formatShortDate(weekDays[0])} — {formatShortDate(weekDays[6])}
          </strong>
        </div>
        <div className="week-toolbar__actions">
          <button
            aria-label="Semana anterior"
            className="icon-button"
            onClick={() => moveWeek(-1)}
            type="button"
          >
            <ChevronLeft aria-hidden="true" size={20} />
          </button>
          <button
            className="text-button"
            onClick={() => setWeek(startOfWeek())}
            type="button"
          >
            Esta semana
          </button>
          <button
            aria-label="Semana siguiente"
            className="icon-button"
            onClick={() => moveWeek(1)}
            type="button"
          >
            <ChevronRight aria-hidden="true" size={20} />
          </button>
        </div>
      </section>

      {habits.length === 0 ? (
        <StatusPanel
          action={
            <HabitDialog onSave={(input) => saveHabit(input)}>
              <Button>
                <Plus aria-hidden="true" size={18} />
                Crear mi primer hábito
              </Button>
            </HabitDialog>
          }
          description="Empieza con algo pequeño que quieras repetir esta semana."
          kind="empty"
          title="Todavía no hay hábitos"
        />
      ) : (
        <div className="habit-list">
          <div aria-hidden="true" className="habit-grid habit-grid--header">
            <span>Hábito</span>
            <div className="week-days">
              {weekDays.map((day) => (
                <span
                  className={toDateKey(day) === todayKey ? "is-today" : ""}
                  key={toDateKey(day)}
                >
                  <small>{formatShortDay(day)}</small>
                  <strong>{day.getDate()}</strong>
                </span>
              ))}
            </div>
            <span>Racha</span>
            <span />
          </div>

          {habits.map((habit) => {
            const summary = summaries.get(habit.id);
            const completedDates = new Set(summary?.check_in_dates ?? []);
            return (
              <article className="habit-grid habit-row" key={habit.id}>
                <div className="habit-identity">
                  <span
                    aria-hidden="true"
                    className="habit-color"
                    style={{ backgroundColor: habit.color }}
                  />
                  <div>
                    <h2>{habit.name}</h2>
                    <p>
                      {summary?.completed_count ?? 0} de{" "}
                      {summary?.target_count ?? 0} esta semana
                    </p>
                    {habit.frequency === "daily" && (
                      <button
                        className="recovery-action"
                        disabled={recoveryMutation.isPending}
                        onClick={() => {
                          setRecoveryMessage(null);
                          recoveryMutation.mutate(habit.id);
                        }}
                        type="button"
                      >
                        <RotateCcw aria-hidden="true" size={14} />
                        Recuperar ayer
                      </button>
                    )}
                    {recoveryMessage?.habitId === habit.id && (
                      <p
                        className={`recovery-message recovery-message--${recoveryMessage.kind}`}
                        role={recoveryMessage.kind === "error" ? "alert" : "status"}
                      >
                        {recoveryMessage.text}
                      </p>
                    )}
                  </div>
                </div>

                <div className="week-days">
                  {weekDays.map((day) => {
                    const date = toDateKey(day);
                    const checked = completedDates.has(date);
                    const action = habit.direction === "avoid"
                      ? checked
                        ? "Desmarcar evitado"
                        : "Marcar como evitado"
                      : checked
                        ? "Desmarcar"
                        : "Marcar";
                    return (
                      <button
                        aria-label={`${action} ${habit.name} el ${formatShortDate(day)}`}
                        aria-pressed={checked}
                        className={`check-button${
                          checked ? " check-button--checked" : ""
                        }`}
                        disabled={checkInMutation.isPending}
                        key={date}
                        onClick={() =>
                          checkInMutation.mutate({
                            checked,
                            date,
                            habitId: habit.id,
                          })
                        }
                        style={
                          checked
                            ? { backgroundColor: habit.color }
                            : undefined
                        }
                        type="button"
                      >
                        {checked && <Check aria-hidden="true" size={16} />}
                      </button>
                    );
                  })}
                </div>

                <div className="streak">
                  <Flame aria-hidden="true" size={17} />
                  <strong>{summary?.current_streak ?? 0}</strong>
                  <span>días</span>
                </div>

                <div className="habit-actions">
                  <HabitDialog
                    habit={habit}
                    isPending={saveMutation.isPending}
                    onSave={(input) => saveHabit(input, habit.id)}
                  >
                    <button
                      aria-label={`Editar ${habit.name}`}
                      className="icon-button"
                      type="button"
                    >
                      <Pencil aria-hidden="true" size={17} />
                    </button>
                  </HabitDialog>
                  <ConfirmDialog
                    description={`“${habit.name}” dejará de aparecer en tu semana. Sus registros se conservarán.`}
                    onConfirm={() => archiveMutation.mutate(habit.id)}
                    title="¿Archivar este hábito?"
                  >
                    <button
                      aria-label={`Archivar ${habit.name}`}
                      className="icon-button"
                      type="button"
                    >
                      <Archive aria-hidden="true" size={17} />
                    </button>
                  </ConfirmDialog>
                  <MoreHorizontal
                    aria-hidden="true"
                    className="habit-actions__mobile"
                    size={18}
                  />
                </div>
              </article>
            );
          })}
        </div>
      )}

      {saveMutation.isError && (
        <p className="inline-error" role="alert">
          No se pudo guardar el hábito. Inténtalo nuevamente.
        </p>
      )}
    </PageFrame>
  );
}

function PageFrame({ children }: { children: React.ReactNode }) {
  return <div className="page page--wide">{children}</div>;
}
