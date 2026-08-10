import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, plannerApi } from "../lib/api";
import type { PlannerUser } from "../types/planner";
import {
  SessionContext,
  type SessionStatus,
} from "./session-store";

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PlannerUser | null>(null);
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [notice, setNotice] = useState<string | null>(null);

  const loadSession = useCallback(async () => {
    setStatus("loading");
    try {
      const currentUser = await plannerApi.getCurrentUser();
      setUser(currentUser);
      setNotice(null);
      setStatus("authenticated");
    } catch (error) {
      setUser(null);
      if (error instanceof ApiError && error.status === 401) {
        setStatus("guest");
        return;
      }
      setNotice("No pudimos comprobar tu sesión. Revisa la conexión.");
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  useEffect(() => {
    const expireSession = () => {
      setUser(null);
      setNotice("Tu sesión terminó. Entra de nuevo para continuar.");
      setStatus("guest");
    };
    window.addEventListener("planner:session-expired", expireSession);
    return () => {
      window.removeEventListener("planner:session-expired", expireSession);
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const currentUser = await plannerApi.login(username, password);
    setUser(currentUser);
    setNotice(null);
    setStatus("authenticated");
    return currentUser;
  }, []);

  const logout = useCallback(async () => {
    try {
      await plannerApi.logout();
    } finally {
      setUser(null);
      setNotice(null);
      setStatus("guest");
    }
  }, []);

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      const currentUser = await plannerApi.changePassword(
        currentPassword,
        newPassword,
      );
      setUser(currentUser);
      setNotice(null);
      setStatus("authenticated");
      return currentUser;
    },
    [],
  );

  const value = useMemo(
    () => ({
      user,
      status,
      notice,
      login,
      logout,
      changePassword,
      retry: loadSession,
    }),
    [changePassword, loadSession, login, logout, notice, status, user],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}
