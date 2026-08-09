import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProgressPage } from "./ProgressPage";

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ProgressPage", () => {
  it("shows level progress and creates a weekly challenge", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/gamification/progress")) {
        return response({
          lifetime_xp: 120,
          available_xp: 90,
          level: 2,
          level_start_xp: 100,
          next_level_xp: 200,
        });
      }
      if (url.endsWith("/gamification/badges")) {
        return response([]);
      }
      if (url.endsWith("/habits")) {
        return response([]);
      }
      if (url.includes("/gamification/rewards")) {
        return response([]);
      }
      if (url.includes("/weekly-challenges") && init?.method === "POST") {
        return response({
          id: 1,
          ...JSON.parse(String(init.body)),
          status: "active",
          progress_count: 0,
          completed_at: null,
          created_at: "2026-08-03T12:00:00Z",
        }, 201);
      }
      if (url.includes("/weekly-challenges")) {
        return response({ detail: "Weekly challenge not found" }, 404);
      }
      return response({});
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={client}>
        <ProgressPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("120 XP acumulado · 90 XP disponible")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Crear desafío" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/gamification/weekly-challenges",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"target_count":3'),
        }),
      );
    });
  });
});
