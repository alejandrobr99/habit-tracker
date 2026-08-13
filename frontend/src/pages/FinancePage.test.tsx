import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FinancePage } from "./FinancePage";

function response(body: unknown, status = 200): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("FinancePage", () => {
  it("loads the month and creates an exact transaction", async () => {
    const category = {
      id: 4,
      name: "Alimentación",
      type: "expense",
      color: "#7A5C3E",
      status: "active",
      created_at: "2026-08-01T12:00:00Z",
      updated_at: "2026-08-01T12:00:00Z",
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/finance/settings")) {
        return response({
          id: 1,
          base_currency: "COP",
          minor_unit: 2,
          created_at: "2026-08-01T12:00:00Z",
          updated_at: "2026-08-01T12:00:00Z",
        });
      }
      if (url.includes("/finance/categories")) {
        return response([category]);
      }
      if (url.includes("/finance/transactions") && init?.method === "POST") {
        return response({
          id: 8,
          ...JSON.parse(String(init.body)),
          created_at: "2026-08-08T12:00:00Z",
          updated_at: "2026-08-08T12:00:00Z",
        }, 201);
      }
      if (url.includes("/finance/transactions") || url.includes("/finance/budgets")) {
        return response([]);
      }
      return response({
        month: "2026-08",
        currency: "COP",
        income_minor: 0,
        expense_minor: 0,
        balance_minor: 0,
        budgeted_minor: 0,
        budget_remaining_minor: 0,
        categories: [],
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={client}>
        <FinancePage />
      </QueryClientProvider>,
    );

    await userEvent.click(
      await screen.findByRole("button", { name: "Registrar movimiento" }),
    );
    await userEvent.type(screen.getByLabelText("Importe"), "1250.50");
    await userEvent.type(screen.getByLabelText("Descripción"), "Mercado");
    await userEvent.click(screen.getByRole("button", { name: "Guardar movimiento" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8000/api/v1/finance/transactions",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining('"amount_minor":125050'),
        }),
      );
    });
  });

  it("edits the base currency while there is no financial data", async () => {
    let currency = "COP";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/finance/settings")) {
        if (init?.method === "PUT") {
          currency = JSON.parse(String(init.body)).base_currency;
        }
        return response({
          id: 1,
          base_currency: currency,
          minor_unit: 2,
          created_at: "2026-08-01T12:00:00Z",
          updated_at: "2026-08-01T12:00:00Z",
        });
      }
      if (
        url.includes("/finance/categories")
        || url.includes("/finance/transactions")
        || url.includes("/finance/budgets")
      ) {
        return response([]);
      }
      return response({
        month: "2026-08",
        currency,
        income_minor: 0,
        expense_minor: 0,
        balance_minor: 0,
        budgeted_minor: 0,
        budget_remaining_minor: 0,
        categories: [],
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={client}>
        <FinancePage />
      </QueryClientProvider>,
    );

    await userEvent.click(
      await screen.findByRole("button", { name: "Editar moneda" }),
    );
    await userEvent.selectOptions(screen.getByLabelText("Moneda"), "USD");
    await userEvent.click(screen.getByRole("button", { name: "Guardar moneda" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://127.0.0.1:8000/api/v1/finance/settings",
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ base_currency: "USD" }),
        }),
      );
    });
    expect(await screen.findByText("Moneda base: USD")).toBeInTheDocument();
  });

  it("explains that currency is locked when financial data exists", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/finance/settings")) {
        return response({
          id: 1,
          base_currency: "COP",
          minor_unit: 2,
          created_at: "2026-08-01T12:00:00Z",
          updated_at: "2026-08-01T12:00:00Z",
        });
      }
      if (url.includes("/finance/transactions")) {
        return response([{
          id: 1,
          type: "expense",
          amount_minor: 1000,
          category_id: 4,
          date: "2026-08-08",
          description: "Dato existente",
          note: null,
          created_at: "2026-08-08T12:00:00Z",
          updated_at: "2026-08-08T12:00:00Z",
        }]);
      }
      if (url.includes("/finance/categories") || url.includes("/finance/budgets")) {
        return response([]);
      }
      return response({
        month: "2026-08",
        currency: "COP",
        income_minor: 0,
        expense_minor: 1000,
        balance_minor: -1000,
        budgeted_minor: 0,
        budget_remaining_minor: 0,
        categories: [],
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={client}>
        <FinancePage />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText(
        "Bloqueada porque existen movimientos o presupuestos. No se realiza conversión.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Editar moneda" }),
    ).not.toBeInTheDocument();
  });
});
