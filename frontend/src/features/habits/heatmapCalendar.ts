import type { HeatmapDay } from "../../types/planner";

export interface HeatmapCalendarMonth {
  key: string;
  label: string;
  weeks: Array<Array<HeatmapDay | null>>;
}

const MONTH_FORMATTER = new Intl.DateTimeFormat("es-ES", {
  month: "long",
  year: "numeric",
});

export function parseDateKey(dateKey: string): Date {
  const [year, month, day] = dateKey.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function monthKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

export function buildHeatmapMonths(
  startDate: string,
  endDate: string,
  days: HeatmapDay[],
): HeatmapCalendarMonth[] {
  const start = parseDateKey(startDate);
  const end = parseDateKey(endDate);
  const daysByDate = new Map(days.map((day) => [day.date, day]));
  const months: HeatmapCalendarMonth[] = [];
  const cursor = new Date(start.getFullYear(), start.getMonth(), 1);

  while (cursor <= end) {
    const key = monthKey(cursor);
    const monthDays = days.filter((day) => day.date.startsWith(`${key}-`));
    const leadingEmpty = (cursor.getDay() + 6) % 7;
    const cells: Array<HeatmapDay | null> = [
      ...Array.from({ length: leadingEmpty }, () => null),
      ...monthDays.map((day) => daysByDate.get(day.date) ?? null),
    ];
    const trailingEmpty = (7 - (cells.length % 7)) % 7;
    cells.push(...Array.from({ length: trailingEmpty }, () => null));

    months.push({
      key,
      label: MONTH_FORMATTER.format(cursor),
      weeks: Array.from(
        { length: cells.length / 7 },
        (_, index) => cells.slice(index * 7, index * 7 + 7),
      ),
    });
    cursor.setMonth(cursor.getMonth() + 1);
  }

  return months;
}
