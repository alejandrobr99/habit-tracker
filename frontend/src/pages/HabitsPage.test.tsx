import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { HabitsPage } from "./HabitsPage";

const habit = {
  id: 7,
  name: "Leer diez páginas",
  description: "Antes de dormir",
  direction: "build",
  frequency: "daily",
  status: "active",
  color: "#71806d",
  created_at: "2026-08-01T12:00:00Z",
  updated_at: "2026-08-01T12:00:00Z",
};

function response(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("HabitsPage", () => {
  it("loads a habit and sends its daily check-in", async () => {
    let checked = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/gamification/progress")) {
        return response({
          lifetime_xp: 260,
          available_xp: 160,
          level: 3,
          level_start_xp: 200,
          next_level_xp: 300,
        });
      }
      if (url.includes("weekly-summary")) {
        return response({
          week_start: "2026-08-03",
          week_end: "2026-08-09",
          habits: [
            {
              habit,
              check_in_dates: checked ? ["2026-08-08"] : [],
              completed_count: checked ? 7 : 6,
              target_count: 7,
              current_streak: checked ? 1 : 0,
            },
          ],
        });
      }
      if (url.endsWith("/habits")) {
        return response([habit]);
      }
      if (init?.method === "PUT") {
        checked = true;
      }
      return response({
        id: 1,
        habit_id: habit.id,
        check_in_date: "2026-08-08",
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
          <HabitsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: habit.name }),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getAllByRole("button", {
        name: new RegExp(`Marcar ${habit.name}`),
      })[0],
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(
          new RegExp(`/habits/${habit.id}/check-ins/\\d{4}-\\d{2}-\\d{2}$`),
        ),
        expect.objectContaining({ method: "PUT" }),
      );
    });
    expect(
      await screen.findByText("El ritmo está completo"),
    ).toBeInTheDocument();
    expect(screen.getByText("días")).toBeInTheDocument();
    expect(screen.getByText("XP disponible: 160")).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: "Recuperar ayer · 120 XP" }),
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `http://localhost:8000/api/v1/habits/${habit.id}/streak-recoveries`,
        expect.objectContaining({
          method: "POST",
          body: expect.stringMatching(
            /^\{"recovered_date":"\d{4}-\d{2}-\d{2}"\}$/,
          ),
        }),
      );
    });
    expect(
      await screen.findByText(
        "La continuidad de tu racha quedó recuperada. Se descontaron 120 XP.",
      ),
    ).toBeInTheDocument();
  });

  it("disables only recovery when available XP is insufficient", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/gamification/progress")) {
        return response({
          lifetime_xp: 90,
          available_xp: 80,
          level: 1,
          level_start_xp: 0,
          next_level_xp: 100,
        });
      }
      if (url.includes("weekly-summary")) {
        return response({
          week_start: "2026-08-03",
          week_end: "2026-08-09",
          habits: [
            {
              habit,
              check_in_dates: [],
              completed_count: 0,
              target_count: 7,
              current_streak: 0,
            },
          ],
        });
      }
      return response([habit]);
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
          <HabitsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const recoveryButton = await screen.findByRole("button", {
      name: "Recuperar ayer · 120 XP",
    });
    expect(screen.getByText("XP disponible: 80")).toBeInTheDocument();
    expect(screen.getByText("Necesitas 120 XP disponibles")).toBeInTheDocument();
    expect(recoveryButton).toBeDisabled();
    expect(
      screen.getAllByRole("button", {
        name: new RegExp(`Marcar ${habit.name}`),
      })[0],
    ).toBeEnabled();
  });
});
