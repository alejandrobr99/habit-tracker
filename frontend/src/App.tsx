import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { FinancePage } from "./pages/FinancePage";
import { HabitsPage } from "./pages/HabitsPage";
import { ProgressPage } from "./pages/ProgressPage";
import { TodayPage } from "./pages/TodayPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route element={<TodayPage />} index />
        <Route element={<HabitsPage />} path="habitos" />
        <Route element={<FinancePage />} path="finanzas" />
        <Route element={<ProgressPage />} path="progreso" />
        <Route element={<Navigate replace to="/" />} path="*" />
      </Route>
    </Routes>
  );
}
