import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { toDateKey } from "../lib/date";
import { TodayPage } from "./TodayPage";

const habit = {
  id: 9,
  name: "Caminar diez minutos",
  description: "Después del almuerzo",
  direction: "build",
  frequency: "daily",
  status: "active",
  color: "#71806d",
  created_at: "2026-08-01T12:00:00Z",
  updated_at: "2026-08-01T12:00:00Z",
};
const completedHabit = {
  ...habit,
  id: 10,
  name: "Preparar el día",
};

function response(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("TodayPage", () => {
  it("shows progress and places pending habits first", async () => {
    const today = toDateKey(new Date());
    let checked = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/gamification/progress")) {
        return response({
          lifetime_xp: 240,
          available_xp: 180,
          level: 3,
          level_start_xp: 200,
          next_level_xp: 300,
        });
      }
      if (url.includes("weekly-summary")) {
        return response({
          week_start: today,
          week_end: today,
          habits: [
            {
              habit: completedHabit,
              check_in_dates: [today],
              completed_count: 1,
              target_count: 7,
              current_streak: 8,
            },
            {
              habit,
              check_in_dates: checked ? [today] : [],
              completed_count: checked ? 1 : 0,
              target_count: 7,
              current_streak: checked ? 1 : 0,
            },
          ],
        });
      }
      if (url.endsWith("/habits")) {
        return response([completedHabit, habit]);
      }
      if (init?.method === "PUT") {
        checked = true;
      }
      return response({
        id: 3,
        habit_id: habit.id,
        check_in_date: today,
        created_at: "2026-08-08T12:00:00Z",
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <TodayPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: habit.name }),
    ).toBeInTheDocument();
    expect(screen.getByText("Nivel")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("240 XP")).toBeInTheDocument();
    expect(screen.getByText("180 XP disponibles")).toBeInTheDocument();
    expect(screen.getByText("8 días")).toBeInTheDocument();
    expect(screen.getByText("Pendientes de hoy")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "1 por registrar hoy" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent),
    ).toEqual([habit.name, completedHabit.name]);
    expect(screen.queryByText(`${habit.name} quedó completado`)).not.toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: `Marcar ${habit.name}` }),
    );

    expect(
      await screen.findByText("Tu día floreció"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(`/habits/${habit.id}/check-ins/${today}$`),
        expect.objectContaining({ method: "PUT" }),
      );
    });
  });
});
