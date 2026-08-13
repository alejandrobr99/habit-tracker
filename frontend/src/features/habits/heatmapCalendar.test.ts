import { describe, expect, it } from "vitest";

import type { HeatmapDay } from "../../types/planner";
import { buildHeatmapMonths } from "./heatmapCalendar";

function day(date: string): HeatmapDay {
  return {
    date,
    completed_count: 0,
    eligible_count: 1,
    percentage: 0,
  };
}

function daysBetween(startDate: string, endDate: string): HeatmapDay[] {
  const [startYear, startMonth, startDay] = startDate.split("-").map(Number);
  const [endYear, endMonth, endDay] = endDate.split("-").map(Number);
  const end = new Date(endYear, endMonth - 1, endDay);
  const cursor = new Date(startYear, startMonth - 1, startDay);
  const days: HeatmapDay[] = [];

  while (cursor <= end) {
    const date = [
      cursor.getFullYear(),
      String(cursor.getMonth() + 1).padStart(2, "0"),
      String(cursor.getDate()).padStart(2, "0"),
    ].join("-");
    days.push(day(date));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

describe("buildHeatmapMonths", () => {
  it("groups three months into Monday-first complete weeks", () => {
    const days = daysBetween("2026-06-01", "2026-08-12");

    const months = buildHeatmapMonths("2026-06-01", "2026-08-12", days);

    expect(months.map((month) => month.key)).toEqual([
      "2026-06",
      "2026-07",
      "2026-08",
    ]);
    expect(months[0].weeks[0][0]?.date).toBe("2026-06-01");
    expect(months[1].weeks[0][2]?.date).toBe("2026-07-01");
    expect(months[2].weeks.flat().at(-1)).toBeNull();
    expect(months.every((month) =>
      month.weeks.every((week) => week.length === 7)
    )).toBe(true);
  });
});
