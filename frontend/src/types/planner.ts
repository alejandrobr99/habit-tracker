export type HabitFrequency = "daily" | "weekly";

export interface Habit {
  id: number;
  name: string;
  description: string | null;
  frequency: HabitFrequency;
  status: "active" | "archived";
  color: string;
  created_at: string;
  updated_at: string;
}

export interface HabitInput {
  name: string;
  description: string | null;
  frequency: HabitFrequency;
  color: string;
}

export interface CheckIn {
  id: number;
  habit_id: number;
  check_in_date: string;
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
