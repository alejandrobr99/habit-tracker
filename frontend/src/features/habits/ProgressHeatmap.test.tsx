import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { plannerApi } from "../../lib/api";
import type {
  HeatmapHabit,
  ProgressHeatmap as ProgressHeatmapData,
} from "../../types/planner";
import { ProgressHeatmap } from "./ProgressHeatmap";

const habits: HeatmapHabit[] = [
  { id: 1, name: "Caminar", frequency: "daily", color: "#71806d" },
  { id: 2, name: "Leer", frequency: "daily", color: "#806a48" },
  { id: 3, name: "Planear", frequency: "weekly", color: "#3f4c43" },
];

const heatmap: ProgressHeatmapData = {
  start_date: "2026-08-01",
  end_date: "2026-08-05",
  months: 1,
  habits,
  days: [
    {
      date: "2026-08-01",
      completed_count: 0,
      eligible_count: 0,
      percentage: null,
    },
    {
      date: "2026-08-02",
      completed_count: 0,
      eligible_count: 2,
      percentage: 0,
    },
    {
      date: "2026-08-03",
      completed_count: 1,
      eligible_count: 3,
      percentage: 33,
    },
    {
      date: "2026-08-04",
      completed_count: 2,
      eligible_count: 3,
      percentage: 67,
    },
    {
      date: "2026-08-05",
      completed_count: 3,
      eligible_count: 3,
      percentage: 100,
    },
    {
      date: "2026-08-06",
      completed_count: 3,
      eligible_count: 4,
      percentage: 75,
    },
  ],
};

afterEach(() => {
  vi.restoreAllMocks();
});

function renderHeatmap(
  componentHabits: HeatmapHabit[] = habits,
): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <ProgressHeatmap habits={componentHabits} />
    </QueryClientProvider>,
  );
  return queryClient;
}

describe("ProgressHeatmap", () => {
  it("renders all visual levels, text labels, and accessible counts", async () => {
    vi.spyOn(plannerApi, "getProgressHeatmap").mockResolvedValue(heatmap);

    renderHeatmap();

    const calendar = await screen.findByRole("table");
    expect(within(calendar).getByText("—")).toBeInTheDocument();
    expect(
      screen.getByRole("cell", {
        name: /1 de agosto de 2026: 0 de 0 hábitos, sin datos/i,
      }),
    ).toBeInTheDocument();
    expect(within(calendar).getByText("0 %")).toBeInTheDocument();
    expect(within(calendar).getByText("33 %")).toBeInTheDocument();
    expect(within(calendar).getByText("67 %")).toBeInTheDocument();
    expect(within(calendar).getByText("75 %")).toBeInTheDocument();
    expect(within(calendar).getByText("100 %")).toBeInTheDocument();
    expect(
      screen.getByRole("cell", {
        name: /5 de agosto de 2026: 3 de 3 hábitos, 100 %/i,
      }),
    ).toHaveClass("heatmap-day--complete");
    expect(
      screen.getByRole("cell", {
        name: /6 de agosto de 2026: 3 de 4 hábitos, 75 %/i,
      }),
    ).toHaveClass("heatmap-day--high");
    expect(screen.getByLabelText("Leyenda del calendario")).toHaveTextContent(
      "Sin datos0 %1–49 %50–74 %75–99 %100 %",
    );
  });

  it("requests three months from the period selector", async () => {
    const getProgressHeatmap = vi
      .spyOn(plannerApi, "getProgressHeatmap")
      .mockResolvedValue(heatmap);
    renderHeatmap();
    await screen.findByRole("table");

    await userEvent.click(screen.getByRole("button", { name: "3 meses" }));

    await waitFor(() => {
      expect(getProgressHeatmap).toHaveBeenCalledWith(3, undefined);
    });
  });

  it("sends exactly two selected habit identifiers", async () => {
    const getProgressHeatmap = vi
      .spyOn(plannerApi, "getProgressHeatmap")
      .mockResolvedValue(heatmap);
    renderHeatmap();
    await screen.findByRole("table");

    await userEvent.click(screen.getByRole("button", { name: "Planear" }));

    await waitFor(() => {
      expect(getProgressHeatmap).toHaveBeenCalledWith(1, [1, 2]);
    });
    expect(screen.getByRole("button", { name: "Caminar" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Leer" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("does not fetch when no habit is selected", async () => {
    const getProgressHeatmap = vi
      .spyOn(plannerApi, "getProgressHeatmap")
      .mockResolvedValue({
        ...heatmap,
        habits: [habits[0]],
      });
    renderHeatmap([habits[0]]);
    await screen.findByRole("table");
    getProgressHeatmap.mockClear();

    await userEvent.click(screen.getByRole("button", { name: "Caminar" }));

    expect(
      screen.getByText("Elige al menos un hábito para ver el historial"),
    ).toBeInTheDocument();
    expect(getProgressHeatmap).not.toHaveBeenCalled();
  });

  it("keeps an endpoint error local and retries it", async () => {
    const getProgressHeatmap = vi
      .spyOn(plannerApi, "getProgressHeatmap")
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockResolvedValueOnce(heatmap);
    renderHeatmap();

    expect(
      await screen.findByText(
        "No pudimos cargar el historial. Inténtalo nuevamente.",
      ),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));

    expect(await screen.findByRole("table")).toBeInTheDocument();
    expect(getProgressHeatmap).toHaveBeenCalledTimes(2);
  });
});
