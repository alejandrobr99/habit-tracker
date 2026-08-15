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
  OcrBudget,
  OcrPreview,
  PlannerUser,
  Progress,
  ProgressHeatmap,
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
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");
const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? "10000");
const API_TIMEOUT_MS =
  Number.isFinite(configuredTimeout) && configuredTimeout > 0
    ? configuredTimeout
    : 10_000;
const OCR_PREVIEW_TIMEOUT_MS = 60_000;

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
    credentials: "include",
    signal: options?.signal ?? AbortSignal.timeout(API_TIMEOUT_MS),
    headers: {
      ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
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
    const error = new ApiError(message, response.status);
    if (
      response.status === 401 &&
      path !== "/auth/login" &&
      typeof window !== "undefined"
    ) {
      window.dispatchEvent(new CustomEvent("planner:session-expired"));
    }
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

async function requestBlob(path: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    signal: AbortSignal.timeout(API_TIMEOUT_MS),
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
  return response.blob();
}

export const plannerApi = {
  login: (username: string, password: string): Promise<PlannerUser> =>
    request<PlannerUser>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: (): Promise<void> =>
    request<void>("/auth/logout", {
      method: "POST",
    }),
  getCurrentUser: (): Promise<PlannerUser> =>
    request<PlannerUser>("/auth/me"),
  changePassword: (
    currentPassword: string,
    newPassword: string,
  ): Promise<PlannerUser> =>
    request<PlannerUser>("/auth/password", {
      method: "PUT",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    }),
  listUsers: (): Promise<PlannerUser[]> =>
    request<PlannerUser[]>("/admin/users"),
  createUser: (input: {
    username: string;
    display_name: string;
    temporary_password: string;
    role: "admin" | "member";
  }): Promise<PlannerUser> =>
    request<PlannerUser>("/admin/users", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  updateUser: (
    id: number,
    input: {
      display_name?: string;
      role?: "admin" | "member";
      status?: "active" | "disabled";
    },
  ): Promise<PlannerUser> =>
    request<PlannerUser>(`/admin/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  resetUserPassword: (id: number, temporaryPassword: string): Promise<void> =>
    request<void>(`/admin/users/${id}/password-reset`, {
      method: "POST",
      body: JSON.stringify({ temporary_password: temporaryPassword }),
    }),
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
  getProgressHeatmap: (
    months: 1 | 3,
    habitIds?: number[],
  ): Promise<ProgressHeatmap> => {
    const params = new URLSearchParams({ months: String(months) });
    habitIds?.forEach((habitId) => {
      params.append("habit_ids", String(habitId));
    });
    return request<ProgressHeatmap>(
      `/habits/progress-heatmap?${params.toString()}`,
    );
  },
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
  listTransactionsRange: (
    startMonth: string,
    endMonth: string,
  ): Promise<FinanceTransaction[]> =>
    request<FinanceTransaction[]>(
      `/finance/transactions/range?start_month=${encodeURIComponent(startMonth)}&end_month=${encodeURIComponent(endMonth)}`,
    ),
  exportTransactions: (months: string[]): Promise<Blob> =>
    requestBlob(
      `/finance/transactions/export-selected?${months.map((month) => `months=${encodeURIComponent(month)}`).join("&")}`,
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
  previewFinanceImport: (file: File): Promise<OcrPreview> => {
    const body = new FormData();
    body.append("file", file);
    return request<OcrPreview>("/finance/imports/preview", {
      method: "POST",
      body,
      signal: AbortSignal.timeout(OCR_PREVIEW_TIMEOUT_MS),
    });
  },
  confirmFinanceImport: (
    token: string,
    rows: TransactionInput[],
  ): Promise<{ imported_count: number; transactions: FinanceTransaction[] }> =>
    request(`/finance/imports/${encodeURIComponent(token)}/confirm`, {
      method: "POST",
      body: JSON.stringify({ rows }),
    }),
  getFinanceImportBudget: (): Promise<OcrBudget> =>
    request<OcrBudget>("/finance/imports/budget"),
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
