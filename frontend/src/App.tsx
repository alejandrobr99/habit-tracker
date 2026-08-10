import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { useSession } from "./context/session-store";
import { AdminPage } from "./pages/AdminPage";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { FinancePage } from "./pages/FinancePage";
import { HabitsPage } from "./pages/HabitsPage";
import { LoginPage } from "./pages/LoginPage";
import { ProgressPage } from "./pages/ProgressPage";
import { TodayPage } from "./pages/TodayPage";

export default function App() {
  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route element={<LoginPage />} path="acceso" />
      </Route>
      <Route element={<Authenticated />}>
        <Route element={<ChangePasswordOnly />}>
          <Route element={<ChangePasswordPage />} path="cambiar-clave" />
        </Route>
        <Route element={<PasswordReady />}>
          <Route element={<AppShell />}>
            <Route element={<TodayPage />} index />
            <Route element={<HabitsPage />} path="habitos" />
            <Route element={<FinancePage />} path="finanzas" />
            <Route element={<ProgressPage />} path="progreso" />
            <Route element={<AdminOnly />}>
              <Route element={<AdminPage />} path="administracion" />
            </Route>
          </Route>
        </Route>
      </Route>
      <Route element={<FallbackRoute />} path="*" />
    </Routes>
  );
}

function Authenticated() {
  const { status } = useSession();
  if (status === "loading") {
    return <SessionLoading />;
  }
  if (status !== "authenticated") {
    return <Navigate replace to="/acceso" />;
  }
  return <Outlet />;
}

function PublicOnly() {
  const { status, user } = useSession();
  if (status === "loading") {
    return <SessionLoading />;
  }
  if (status === "authenticated") {
    return (
      <Navigate replace to={user?.must_change_password ? "/cambiar-clave" : "/"} />
    );
  }
  return <Outlet />;
}

function PasswordReady() {
  const { user } = useSession();
  return user?.must_change_password ? (
    <Navigate replace to="/cambiar-clave" />
  ) : (
    <Outlet />
  );
}

function ChangePasswordOnly() {
  const { user } = useSession();
  return user?.must_change_password ? <Outlet /> : <Navigate replace to="/" />;
}

function AdminOnly() {
  const { user } = useSession();
  return user?.role === "admin" ? <Outlet /> : <Navigate replace to="/" />;
}

function FallbackRoute() {
  const { status, user } = useSession();
  if (status === "loading") {
    return <SessionLoading />;
  }
  if (status !== "authenticated") {
    return <Navigate replace to="/acceso" />;
  }
  return (
    <Navigate replace to={user?.must_change_password ? "/cambiar-clave" : "/"} />
  );
}

function SessionLoading() {
  return (
    <main aria-busy="true" className="session-loading">
      <span className="brand__mark" />
      <p>Preparando tu espacio…</p>
    </main>
  );
}
