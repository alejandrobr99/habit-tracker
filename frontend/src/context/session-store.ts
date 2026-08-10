import { createContext, useContext } from "react";

import type { PlannerUser } from "../types/planner";

export type SessionStatus = "loading" | "authenticated" | "guest" | "error";

export interface SessionContextValue {
  user: PlannerUser | null;
  status: SessionStatus;
  notice: string | null;
  login: (username: string, password: string) => Promise<PlannerUser>;
  logout: () => Promise<void>;
  changePassword: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<PlannerUser>;
  retry: () => Promise<void>;
}

export const SessionContext = createContext<SessionContextValue | null>(null);

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return context;
}
