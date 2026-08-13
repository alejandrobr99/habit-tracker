import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState, type CSSProperties } from "react";

import { Button } from "../../components/ui/Button";
import { plannerApi } from "../../lib/api";
import type { HeatmapDay, HeatmapHabit } from "../../types/planner";
import { buildHeatmapMonths, parseDateKey } from "./heatmapCalendar";

interface ProgressHeatmapProps {
  habits: HeatmapHabit[];
}

const WEEK_DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const DATE_FORMATTER = new Intl.DateTimeFormat("es-ES", {
  day: "numeric",
  month: "long",
  weekday: "long",
  year: "numeric",
});

function getDayStyle(day: HeatmapDay): CSSProperties | undefined {
  if (day.percentage === null) {
    return undefined;
  }
  return {
    "--heatmap-progress": `${day.percentage}%`,
  } as CSSProperties;
}

function getAccessibleDayLabel(day: HeatmapDay): string {
  const date = DATE_FORMATTER.format(parseDateKey(day.date));
  const result = day.percentage === null ? "Sin datos" : `${day.percentage} %`;
  return `${date}: ${day.completed_count} de ${day.eligible_count} hábitos, ${result}`;
}

export function ProgressHeatmap({ habits }: ProgressHeatmapProps) {
  const [months, setMonths] = useState<1 | 3>(1);
  const [selectedHabitIds, setSelectedHabitIds] = useState<Set<number>>(
    () => new Set(habits.map((habit) => habit.id)),
  );
  const previousHabitIds = useRef(habits.map((habit) => habit.id));
  const activeHabitKey = habits.map((habit) => habit.id).join(",");

  useEffect(() => {
    const activeIds = habits.map((habit) => habit.id);
    setSelectedHabitIds((current) => {
      const previouslyAllSelected = previousHabitIds.current.every((id) =>
        current.has(id)
      );
      const next = previouslyAllSelected
        ? new Set(activeIds)
        : new Set(activeIds.filter((id) => current.has(id)));
      previousHabitIds.current = activeIds;
      return next;
    });
  }, [activeHabitKey, habits]);

  const selectedIds = [...selectedHabitIds].sort((first, second) => first - second);
  const allSelected =
    habits.length > 0 && selectedIds.length === habits.length;
  const heatmapQuery = useQuery({
    queryKey: ["progress-heatmap", months, selectedIds],
    queryFn: () =>
      plannerApi.getProgressHeatmap(
        months,
        allSelected ? undefined : selectedIds,
      ),
    enabled: selectedIds.length > 0,
  });
  const calendarMonths = heatmapQuery.data
    ? buildHeatmapMonths(
        heatmapQuery.data.start_date,
        heatmapQuery.data.end_date,
        heatmapQuery.data.days,
      )
    : [];
  const hasActivity = heatmapQuery.data?.days.some(
    (day) => day.completed_count > 0,
  );

  function toggleHabit(habitId: number) {
    setSelectedHabitIds((current) => {
      const next = new Set(current);
      if (next.has(habitId)) {
        next.delete(habitId);
      } else {
        next.add(habitId);
      }
      return next;
    });
  }

  return (
    <section aria-labelledby="progress-history-title" className="heatmap-section">
      <div className="heatmap-section__heading">
        <div>
          <span className="eyebrow">Historial</span>
          <h2 id="progress-history-title">Calendario de progreso</h2>
          <p>Consulta tus registros por fecha. Este calendario es de solo lectura.</p>
        </div>
        <div
          aria-label="Periodo del historial"
          className="heatmap-period"
          role="group"
        >
          <button
            aria-pressed={months === 1}
            onClick={() => setMonths(1)}
            type="button"
          >
            1 mes
          </button>
          <button
            aria-pressed={months === 3}
            onClick={() => setMonths(3)}
            type="button"
          >
            3 meses
          </button>
        </div>
      </div>

      <div
        aria-label="Filtrar historial por hábitos"
        className="heatmap-filters"
        role="group"
      >
        <button
          aria-pressed={allSelected}
          className="heatmap-filter"
          onClick={() =>
            setSelectedHabitIds(
              allSelected
                ? new Set()
                : new Set(habits.map((habit) => habit.id)),
            )
          }
          type="button"
        >
          Todos
        </button>
        {habits.map((habit) => (
          <button
            aria-pressed={selectedHabitIds.has(habit.id)}
            className="heatmap-filter"
            key={habit.id}
            onClick={() => toggleHabit(habit.id)}
            type="button"
          >
            <span
              aria-hidden="true"
              className="heatmap-filter__color"
              style={{ backgroundColor: habit.color }}
            />
            {habit.name}
          </button>
        ))}
      </div>

      {selectedIds.length === 0 ? (
        <p className="heatmap-status">
          Elige al menos un hábito para ver el historial
        </p>
      ) : heatmapQuery.isLoading ? (
        <p className="heatmap-status" role="status">
          Cargando historial.
        </p>
      ) : heatmapQuery.isError ? (
        <div className="heatmap-status heatmap-status--error" role="alert">
          <p>No pudimos cargar el historial. Inténtalo nuevamente.</p>
          <Button
            onClick={() => void heatmapQuery.refetch()}
            variant="secondary"
          >
            Reintentar
          </Button>
        </div>
      ) : (
        <>
          {!hasActivity && (
            <p className="heatmap-activity">Sin registros en este periodo</p>
          )}
          <div className="heatmap-months" data-months={months}>
            {calendarMonths.map((month) => (
              <section
                aria-labelledby={`heatmap-month-${month.key}`}
                className="heatmap-month"
                key={month.key}
              >
                <h3 id={`heatmap-month-${month.key}`}>{month.label}</h3>
                <table>
                  <caption className="sr-only">
                    Progreso diario de {month.label}
                  </caption>
                  <thead>
                    <tr>
                      {WEEK_DAYS.map((weekDay) => (
                        <th key={weekDay} scope="col">
                          {weekDay}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {month.weeks.map((week, weekIndex) => (
                      <tr key={`${month.key}-${weekIndex}`}>
                        {week.map((day, dayIndex) =>
                          day ? (
                            <td
                              aria-label={getAccessibleDayLabel(day)}
                              className="heatmap-day"
                              data-dark-background={
                                day.percentage !== null && day.percentage >= 60
                              }
                              key={day.date}
                              style={getDayStyle(day)}
                            >
                              <span>{parseDateKey(day.date).getDate()}</span>
                              <strong>
                                {day.percentage === null
                                  ? "—"
                                  : `${day.percentage} %`}
                              </strong>
                            </td>
                          ) : (
                            <td
                              aria-hidden="true"
                              className="heatmap-day heatmap-day--empty"
                              key={`${month.key}-${weekIndex}-${dayIndex}`}
                            />
                          ),
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            ))}
          </div>
          <div aria-label="Leyenda del calendario" className="heatmap-legend">
            {[
              ["none", "Sin datos"],
              ["zero", "0 %"],
              ["gradient", "Progreso gradual"],
              ["complete", "100 %"],
            ].map(([level, label]) => (
              <span key={level}>
                <i
                  aria-hidden="true"
                  className={`heatmap-legend__swatch heatmap-day--${level}`}
                />
                {label}
              </span>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
