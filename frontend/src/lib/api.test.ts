import { afterEach, describe, expect, it, vi } from "vitest";

import { plannerApi } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("plannerApi", () => {
  it("sends the backend contract when creating a habit", async () => {
    const habit = {
      id: 1,
      name: "Caminar",
      description: null,
      direction: "build",
      frequency: "daily",
      status: "active",
      color: "#71806d",
      created_at: "2026-08-08T12:00:00Z",
      updated_at: "2026-08-08T12:00:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(habit), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await plannerApi.createHabit({
      name: "Caminar",
      description: null,
      direction: "build",
      frequency: "daily",
      color: "#71806d",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/habits",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "Caminar",
          description: null,
          direction: "build",
          frequency: "daily",
          color: "#71806d",
        }),
        signal: expect.any(AbortSignal),
      }),
    );
  });

  it("surfaces the API detail and status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Habit not found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(plannerApi.archiveHabit(99)).rejects.toMatchObject({
      message: "Habit not found",
      name: "ApiError",
      status: 404,
    });
  });

  it("accepts an empty response when removing a check-in", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );

    await expect(
      plannerApi.removeCheckIn(1, "2026-08-08"),
    ).resolves.toBeUndefined();
  });
});
