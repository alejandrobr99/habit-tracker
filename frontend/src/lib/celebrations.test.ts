import { describe, expect, it } from "vitest";

import type { HabitWeeklySummary } from "../types/planner";
import { selectCheckInSpectacle } from "./celebrations";

function summary(
  completedCount: number,
  streak: number,
  dates: string[] = [],
): HabitWeeklySummary {
  return {
    habit: {
      id: 1,
      name: "Caminar",
      description: null,
      direction: "build",
      frequency: "daily",
      status: "active",
      color: "#71806d",
      created_at: "2026-08-01T12:00:00Z",
      updated_at: "2026-08-01T12:00:00Z",
    },
    check_in_dates: dates,
    completed_count: completedCount,
    target_count: 7,
    current_streak: streak,
  };
}

describe("selectCheckInSpectacle", () => {
  it("prioritizes completing the day", () => {
    const moment = selectCheckInSpectacle({
      before: summary(6, 6),
      after: summary(7, 7, ["2026-08-08"]),
      date: "2026-08-08",
      summaries: [summary(7, 7, ["2026-08-08"])],
      todayKey: "2026-08-08",
    });

    expect(moment?.kind).toBe("day");
  });

  it("recognizes a weekly target before a streak milestone", () => {
    const moment = selectCheckInSpectacle({
      before: summary(6, 6),
      after: summary(7, 7),
      date: "2026-08-07",
      summaries: [summary(7, 7)],
      todayKey: "2026-08-08",
    });

    expect(moment?.kind).toBe("target");
  });

  it("recognizes defined streak milestones", () => {
    const moment = selectCheckInSpectacle({
      before: summary(2, 2),
      after: summary(3, 3),
      date: "2026-08-07",
      summaries: [summary(3, 3)],
      todayKey: "2026-08-08",
    });

    expect(moment).toMatchObject({
      kind: "streak",
      value: 3,
      unit: "días",
    });
  });
});
