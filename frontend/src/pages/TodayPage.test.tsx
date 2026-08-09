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

function response(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("TodayPage", () => {
  it("celebrates only after a confirmed check-in", async () => {
    const today = toDateKey(new Date());
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("weekly-summary")) {
        return response({
          week_start: today,
          week_end: today,
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
      if (url.endsWith("/habits")) {
        return response([habit]);
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
    expect(screen.queryByText(`${habit.name} quedó completado`)).not.toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: `Marcar ${habit.name}` }),
    );

    expect(
      await screen.findByText(`${habit.name} quedó completado`),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringMatching(`/habits/${habit.id}/check-ins/${today}$`),
        expect.objectContaining({ method: "PUT" }),
      );
    });
  });
});
