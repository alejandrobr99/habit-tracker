export type HabitFrequency = "daily" | "weekly";
export type HabitDirection = "build" | "avoid";
export type ResourceStatus = "active" | "archived";
export type UserRole = "admin" | "member";
export type UserStatus = "active" | "disabled";

export interface PlannerUser {
  id: number;
  username: string;
  display_name: string;
  role: UserRole;
  status: UserStatus;
  must_change_password: boolean;
  created_at: string;
  updated_at: string;
}
export type FinanceType = "income" | "expense";

export interface Habit {
  id: number;
  name: string;
  description: string | null;
  direction: HabitDirection;
  frequency: HabitFrequency;
  status: ResourceStatus;
  color: string;
  created_at: string;
  updated_at: string;
}

export interface HabitInput {
  name: string;
  description: string | null;
  direction: HabitDirection;
  frequency: HabitFrequency;
  color: string;
}

export interface CheckIn {
  id: number;
  habit_id: number;
  check_in_date: string;
  created_at: string;
}

export interface StreakRecovery {
  id: number;
  habit_id: number;
  recovered_date: string;
  created_at: string;
}

export interface HabitWeeklySummary {
  habit: Habit;
  check_in_dates: string[];
  completed_count: number;
  target_count: number;
  current_streak: number;
}

export interface WeeklySummary {
  week_start: string;
  week_end: string;
  habits: HabitWeeklySummary[];
}

export interface HeatmapHabit {
  id: number;
  name: string;
  frequency: HabitFrequency;
  color: string;
}

export interface HeatmapDay {
  date: string;
  completed_count: number;
  eligible_count: number;
  percentage: number | null;
}

export interface ProgressHeatmap {
  start_date: string;
  end_date: string;
  months: 1 | 3;
  habits: HeatmapHabit[];
  days: HeatmapDay[];
}

export interface FinanceSettings {
  id: number;
  base_currency: string;
  minor_unit: number;
  created_at: string;
  updated_at: string;
}

export interface FinanceCategory {
  id: number;
  name: string;
  type: FinanceType;
  color: string;
  status: ResourceStatus;
  created_at: string;
  updated_at: string;
}

export interface CategoryInput {
  name: string;
  type: FinanceType;
  color: string;
}

export interface FinanceTransaction {
  id: number;
  type: FinanceType;
  amount_minor: number;
  category_id: number;
  date: string;
  description: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionInput {
  type: FinanceType;
  amount_minor: number;
  category_id: number;
  date: string;
  description: string;
  note: string | null;
}

export interface Budget {
  id: number;
  month: string;
  category_id: number;
  limit_minor: number;
  created_at: string;
  updated_at: string;
}

export interface SummaryCategory {
  category_id: number;
  category_name: string;
  type: FinanceType;
  actual_minor: number;
  budget_minor: number | null;
  remaining_minor: number | null;
}

export interface MonthlySummary {
  month: string;
  currency: string;
  income_minor: number;
  expense_minor: number;
  balance_minor: number;
  budgeted_minor: number;
  budget_remaining_minor: number;
  categories: SummaryCategory[];
}

export interface Progress {
  lifetime_xp: number;
  available_xp: number;
  level: number;
  level_start_xp: number;
  next_level_xp: number;
}

export interface Badge {
  code:
    | "first_step"
    | "steady_seven"
    | "challenge_complete"
    | "budget_ready"
    | "weekly_reviewed"
    | "reward_claimed";
  name: string;
  description: string;
  awarded: boolean;
  awarded_at: string | null;
}

export interface WeeklyChallenge {
  id: number;
  week_start: string;
  habit_id: number | null;
  target_count: number;
  status: "active" | "completed" | "expired";
  progress_count: number;
  completed_at: string | null;
  created_at: string;
}

export interface WeeklyChallengeInput {
  week_start: string;
  habit_id: number | null;
  target_count: number;
}

export interface Reward {
  id: number;
  name: string;
  description: string | null;
  cost_xp: number;
  status: ResourceStatus;
  created_at: string;
  updated_at: string;
}

export interface RewardInput {
  name: string;
  description: string | null;
  cost_xp: number;
}

export interface RewardRedemption {
  id: number;
  reward_id: number;
  cost_xp: number;
  idempotency_key: string;
  redeemed_at: string;
}

export interface FinanceWeeklyReview {
  id: number;
  week_start: string;
  created_at: string;
}
