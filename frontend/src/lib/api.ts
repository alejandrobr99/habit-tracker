import type {
  CheckIn,
  Habit,
  HabitInput,
  WeeklySummary,
} from "../types/planner";

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;

  constructor(
    message: string,
    status: number,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let message = "No pudimos completar la solicitud.";
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // The fallback message is used when the API does not return JSON.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const plannerApi = {
  listHabits: (): Promise<Habit[]> => request<Habit[]>("/habits"),
  createHabit: (input: HabitInput): Promise<Habit> =>
    request<Habit>("/habits", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateHabit: (id: number, input: HabitInput): Promise<Habit> =>
    request<Habit>(`/habits/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  archiveHabit: (id: number): Promise<Habit> =>
    request<Habit>(`/habits/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "archived" }),
    }),
  checkIn: (habitId: number, date: string): Promise<CheckIn> =>
    request<CheckIn>(`/habits/${habitId}/check-ins/${date}`, {
      method: "PUT",
    }),
  removeCheckIn: (habitId: number, date: string): Promise<void> =>
    request<void>(`/habits/${habitId}/check-ins/${date}`, {
      method: "DELETE",
    }),
  getWeeklySummary: (weekStart: string): Promise<WeeklySummary> =>
    request<WeeklySummary>(
      `/habits/weekly-summary?week_start=${encodeURIComponent(weekStart)}`,
    ),
};
