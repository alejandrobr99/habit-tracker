import type {
  Badge,
  Budget,
  CategoryInput,
  CheckIn,
  FinanceCategory,
  FinanceSettings,
  FinanceTransaction,
  FinanceWeeklyReview,
  Habit,
  HabitInput,
  MonthlySummary,
  Progress,
  ResourceStatus,
  Reward,
  RewardInput,
  RewardRedemption,
  StreakRecovery,
  TransactionInput,
  WeeklyChallenge,
  WeeklyChallengeInput,
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
      method: "DELETE",
    }),
  checkIn: (habitId: number, date: string): Promise<CheckIn> =>
    request<CheckIn>(`/habits/${habitId}/check-ins/${date}`, {
      method: "PUT",
    }),
  removeCheckIn: (habitId: number, date: string): Promise<void> =>
    request<void>(`/habits/${habitId}/check-ins/${date}`, {
      method: "DELETE",
    }),
  createStreakRecovery: (
    habitId: number,
    recoveredDate: string,
  ): Promise<StreakRecovery> =>
    request<StreakRecovery>(`/habits/${habitId}/streak-recoveries`, {
      method: "POST",
      body: JSON.stringify({ recovered_date: recoveredDate }),
    }),
  getWeeklySummary: (weekStart: string): Promise<WeeklySummary> =>
    request<WeeklySummary>(
      `/habits/weekly-summary?week_start=${encodeURIComponent(weekStart)}`,
    ),
  getFinanceSettings: (): Promise<FinanceSettings> =>
    request<FinanceSettings>("/finance/settings"),
  putFinanceSettings: (baseCurrency: string): Promise<FinanceSettings> =>
    request<FinanceSettings>("/finance/settings", {
      method: "PUT",
      body: JSON.stringify({ base_currency: baseCurrency }),
    }),
  listCategories: (status: ResourceStatus = "active"): Promise<FinanceCategory[]> =>
    request<FinanceCategory[]>(
      `/finance/categories?status=${encodeURIComponent(status)}`,
    ),
  createCategory: (input: CategoryInput): Promise<FinanceCategory> =>
    request<FinanceCategory>("/finance/categories", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateCategory: (
    id: number,
    input: Partial<CategoryInput>,
  ): Promise<FinanceCategory> =>
    request<FinanceCategory>(`/finance/categories/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  archiveCategory: (id: number): Promise<void> =>
    request<void>(`/finance/categories/${id}`, { method: "DELETE" }),
  listTransactions: (month: string): Promise<FinanceTransaction[]> =>
    request<FinanceTransaction[]>(
      `/finance/transactions?month=${encodeURIComponent(month)}`,
    ),
  createTransaction: (input: TransactionInput): Promise<FinanceTransaction> =>
    request<FinanceTransaction>("/finance/transactions", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateTransaction: (
    id: number,
    input: TransactionInput,
  ): Promise<FinanceTransaction> =>
    request<FinanceTransaction>(`/finance/transactions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  deleteTransaction: (id: number): Promise<void> =>
    request<void>(`/finance/transactions/${id}`, { method: "DELETE" }),
  listBudgets: (month: string): Promise<Budget[]> =>
    request<Budget[]>(
      `/finance/budgets?month=${encodeURIComponent(month)}`,
    ),
  putBudget: (
    month: string,
    categoryId: number,
    limitMinor: number,
  ): Promise<Budget> =>
    request<Budget>(
      `/finance/budgets/${encodeURIComponent(month)}/${categoryId}`,
      {
        method: "PUT",
        body: JSON.stringify({ limit_minor: limitMinor }),
      },
    ),
  deleteBudget: (month: string, categoryId: number): Promise<void> =>
    request<void>(
      `/finance/budgets/${encodeURIComponent(month)}/${categoryId}`,
      { method: "DELETE" },
    ),
  getMonthlySummary: (month: string): Promise<MonthlySummary> =>
    request<MonthlySummary>(
      `/finance/summary?month=${encodeURIComponent(month)}`,
    ),
  getProgress: (): Promise<Progress> =>
    request<Progress>("/gamification/progress"),
  listBadges: (): Promise<Badge[]> =>
    request<Badge[]>("/gamification/badges"),
  getWeeklyChallenge: (weekStart: string): Promise<WeeklyChallenge> =>
    request<WeeklyChallenge>(
      `/gamification/weekly-challenges?week_start=${encodeURIComponent(weekStart)}`,
    ),
  createWeeklyChallenge: (
    input: WeeklyChallengeInput,
  ): Promise<WeeklyChallenge> =>
    request<WeeklyChallenge>("/gamification/weekly-challenges", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  deleteWeeklyChallenge: (id: number): Promise<void> =>
    request<void>(`/gamification/weekly-challenges/${id}`, {
      method: "DELETE",
    }),
  listRewards: (status: ResourceStatus = "active"): Promise<Reward[]> =>
    request<Reward[]>(
      `/gamification/rewards?status=${encodeURIComponent(status)}`,
    ),
  createReward: (input: RewardInput): Promise<Reward> =>
    request<Reward>("/gamification/rewards", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateReward: (id: number, input: RewardInput): Promise<Reward> =>
    request<Reward>(`/gamification/rewards/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  archiveReward: (id: number): Promise<void> =>
    request<void>(`/gamification/rewards/${id}`, { method: "DELETE" }),
  redeemReward: (
    rewardId: number,
    idempotencyKey: string,
  ): Promise<RewardRedemption> =>
    request<RewardRedemption>("/gamification/reward-redemptions", {
      method: "POST",
      body: JSON.stringify({
        reward_id: rewardId,
        idempotency_key: idempotencyKey,
      }),
    }),
  putFinanceReview: (weekStart: string): Promise<FinanceWeeklyReview> =>
    request<FinanceWeeklyReview>(
      `/gamification/finance-reviews/${encodeURIComponent(weekStart)}`,
      { method: "PUT" },
    ),
};
