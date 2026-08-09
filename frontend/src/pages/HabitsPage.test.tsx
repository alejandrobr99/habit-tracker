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
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
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
      if (url.endsWith("/habits")) {
        return response([habit]);
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

    await userEvent.click(
      screen.getByRole("button", { name: "Recuperar ayer" }),
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
        "Ayer quedó recuperado para la continuidad de tu racha.",
      ),
    ).toBeInTheDocument();
  });
});
