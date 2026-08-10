import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { SessionProvider } from "./context/SessionContext";
import { ApiError, plannerApi } from "./lib/api";
import type { PlannerUser } from "./types/planner";

const baseUser: PlannerUser = {
  id: 1,
  username: "admin",
  display_name: "Administradora",
  role: "admin",
  status: "active",
  must_change_password: false,
  created_at: "2026-08-09T20:00:00Z",
  updated_at: "2026-08-09T20:00:00Z",
};

describe("sesión y rutas privadas", () => {
  it("permite entrar y fuerza el cambio de una clave temporal", async () => {
    vi.spyOn(plannerApi, "getCurrentUser").mockRejectedValue(
      new ApiError("Sesión requerida.", 401),
    );
    vi.spyOn(plannerApi, "login").mockResolvedValue({
      ...baseUser,
      must_change_password: true,
    });
    const user = userEvent.setup();
    renderApplication("/acceso");

    await user.type(await screen.findByLabelText("Usuario"), "admin");
    await user.type(screen.getByLabelText("Contraseña"), "temporal-segura");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(
      await screen.findByRole("heading", { name: "Elige tu contraseña" }),
    ).toBeInTheDocument();
  });

  it("redirige una sesión con cambio pendiente fuera del planificador", async () => {
    vi.spyOn(plannerApi, "getCurrentUser").mockResolvedValue({
      ...baseUser,
      must_change_password: true,
    });
    renderApplication("/");

    expect(
      await screen.findByRole("heading", { name: "Elige tu contraseña" }),
    ).toBeInTheDocument();
  });

  it("muestra administración solo a una cuenta administradora", async () => {
    vi.spyOn(plannerApi, "getCurrentUser").mockResolvedValue(baseUser);
    vi.spyOn(plannerApi, "listUsers").mockResolvedValue([baseUser]);
    renderApplication("/administracion");

    expect(
      await screen.findByRole("heading", { name: "Administración" }),
    ).toBeInTheDocument();
    expect(screen.getByText("@admin")).toBeInTheDocument();
  });
});

function renderApplication(initialEntry: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <SessionProvider>
          <App />
        </SessionProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
