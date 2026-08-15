import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ChevronDown, Pencil, Plus, Trash2, X } from "lucide-react";
import {
  type FormEvent,
  type ReactNode,
  useMemo,
  useState,
} from "react";

import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { StatusPanel } from "../components/ui/StatusPanel";
import { FinanceImportPanel } from "../features/finance/FinanceImportPanel";
import { ApiError, plannerApi } from "../lib/api";
import { toDateKey } from "../lib/date";
import type {
  CategoryInput,
  FinanceCategory,
  FinanceTransaction,
  FinanceType,
  MonthlySummary,
  TransactionInput,
} from "../types/planner";

const categoryColors = ["#7A5C3E", "#536B57", "#315C7A", "#956F35"];
type CaptureMode = "manual" | "automatic";

function currentMonth(): string {
  return toDateKey(new Date()).slice(0, 7);
}

function monthRange(anchor: string, count: number): string[] {
  const [year, month] = anchor.split("-").map(Number);
  return Array.from({ length: count }, (_, index) => {
    const date = new Date(year, month - 1 - index, 1);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  });
}

function parseMoney(value: string, minorUnit: number): number | null {
  const normalized = value.trim().replace(",", ".");
  const pattern = minorUnit === 0
    ? /^\d+$/
    : new RegExp(`^\\d+(?:\\.\\d{1,${minorUnit}})?$`);
  if (!pattern.test(normalized)) {
    return null;
  }
  const [whole, fraction = ""] = normalized.split(".");
  const minor = BigInt(whole) * 10n ** BigInt(minorUnit)
    + BigInt(fraction.padEnd(minorUnit, "0") || "0");
  if (minor <= 0n || minor > BigInt(Number.MAX_SAFE_INTEGER)) {
    return null;
  }
  return Number(minor);
}

function formatMoney(amount: number, currency: string, minorUnit: number): string {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency,
    minimumFractionDigits: minorUnit,
    maximumFractionDigits: minorUnit,
  }).format(amount / 10 ** minorUnit);
}

export function FinancePage() {
  const [month, setMonth] = useState(currentMonth);
  const [captureMode, setCaptureMode] = useState<CaptureMode>("manual");
  const [currencyConflict, setCurrencyConflict] = useState(false);
  const [currencyFeedback, setCurrencyFeedback] = useState("");
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["finance-settings"],
    queryFn: plannerApi.getFinanceSettings,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
  const hasSettings = Boolean(settingsQuery.data);
  const categoriesQuery = useQuery({
    queryKey: ["finance-categories"],
    queryFn: () => plannerApi.listCategories(),
    enabled: hasSettings,
  });
  const transactionsQuery = useQuery({
    queryKey: ["finance-transactions", month],
    queryFn: () => plannerApi.listTransactions(month),
    enabled: hasSettings,
  });
  const budgetsQuery = useQuery({
    queryKey: ["finance-budgets", month],
    queryFn: () => plannerApi.listBudgets(month),
    enabled: hasSettings,
  });
  const summaryMonths = monthRange(month, 6);
  const summaryQuery = useQuery({
    queryKey: ["finance-summary", month],
    queryFn: () => plannerApi.getMonthlySummary(month),
    enabled: hasSettings,
  });
  const historicalSummaryQueries = useQueries({
    queries: summaryMonths.slice(1).map((summaryMonth) => ({
      queryKey: ["finance-summary", summaryMonth],
      queryFn: () => plannerApi.getMonthlySummary(summaryMonth),
      enabled: hasSettings,
    })),
  });

  async function refreshFinance() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["finance-transactions"] }),
      queryClient.invalidateQueries({ queryKey: ["finance-budgets"] }),
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] }),
    ]);
  }

  const settingsMutation = useMutation({
    mutationFn: plannerApi.putFinanceSettings,
    onMutate: () => {
      setCurrencyConflict(false);
      setCurrencyFeedback("");
    },
    onSuccess: async () => {
      setCurrencyFeedback("Moneda base actualizada.");
      await queryClient.invalidateQueries({ queryKey: ["finance-settings"] });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        setCurrencyConflict(true);
      }
    },
  });
  const categoryMutation = useMutation({
    mutationFn: ({ id, input }: { id?: number; input: CategoryInput }) =>
      id
        ? plannerApi.updateCategory(id, input)
        : plannerApi.createCategory(input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["finance-categories"] });
    },
  });
  const archiveCategoryMutation = useMutation({
    mutationFn: plannerApi.archiveCategory,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["finance-categories"] });
    },
  });
  const transactionMutation = useMutation({
    mutationFn: ({ id, input }: { id?: number; input: TransactionInput }) =>
      id
        ? plannerApi.updateTransaction(id, input)
        : plannerApi.createTransaction(input),
    onSuccess: refreshFinance,
  });
  const deleteTransactionMutation = useMutation({
    mutationFn: plannerApi.deleteTransaction,
    onSuccess: refreshFinance,
  });
  const budgetMutation = useMutation({
    mutationFn: ({
      categoryId,
      limitMinor,
    }: {
      categoryId: number;
      limitMinor: number;
    }) => plannerApi.putBudget(month, categoryId, limitMinor),
    onSuccess: refreshFinance,
  });
  const deleteBudgetMutation = useMutation({
    mutationFn: (categoryId: number) => plannerApi.deleteBudget(month, categoryId),
    onSuccess: refreshFinance,
  });

  const missingSettings = settingsQuery.error instanceof ApiError
    && settingsQuery.error.status === 404;
  if (settingsQuery.isLoading) {
    return <FinanceFrame><StatusPanel kind="loading" title="Cargando finanzas" description="Preparando tu información financiera." /></FinanceFrame>;
  }
  if (missingSettings) {
    return (
      <FinanceFrame>
        <CurrencyOnboarding
          error={settingsMutation.isError}
          pending={settingsMutation.isPending}
          onSave={(currency) => settingsMutation.mutate(currency)}
        />
      </FinanceFrame>
    );
  }
  if (settingsQuery.isError || !settingsQuery.data) {
    return (
      <FinanceFrame>
        <StatusPanel
          action={<Button variant="secondary" onClick={() => void settingsQuery.refetch()}>Reintentar</Button>}
          kind="error"
          title="No pudimos cargar finanzas"
          description="Revisa que la API esté disponible e inténtalo de nuevo."
        />
      </FinanceFrame>
    );
  }

  const isLoading = categoriesQuery.isLoading
    || transactionsQuery.isLoading
    || budgetsQuery.isLoading
    || summaryQuery.isLoading;
  const hasError = categoriesQuery.isError
    || transactionsQuery.isError
    || budgetsQuery.isError
    || summaryQuery.isError;
  const categories = categoriesQuery.data ?? [];
  const transactions = transactionsQuery.data ?? [];
  const budgets = budgetsQuery.data ?? [];
  const summary = summaryQuery.data;
  const monthlySummaries = [
    ...(summary ? [summary] : []),
    ...historicalSummaryQueries.flatMap((query) => (query.data ? [query.data] : [])),
  ];
  const { base_currency: currency, minor_unit: minorUnit } = settingsQuery.data;
  const currencyLocked = currencyConflict
    || transactions.length > 0
    || budgets.length > 0;

  return (
    <FinanceFrame>
      <header className="page-header page-header--finance">
        <div>
          <span className="eyebrow">Panorama mensual</span>
          <h1>Finanzas</h1>
          <FinanceCapture
            categories={categories}
            captureMode={captureMode}
            minorUnit={minorUnit}
            onCaptureModeChange={setCaptureMode}
            onConfirmed={refreshFinance}
            onCreateCategory={(input) => categoryMutation.mutateAsync({ input }) as Promise<FinanceCategory>}
            onSaveTransaction={(input) => transactionMutation.mutateAsync({ input })}
            onSaveExistingTransaction={(id, input) => transactionMutation.mutateAsync({ id, input })}
            onDeleteTransaction={(id) => deleteTransactionMutation.mutate(id)}
            pending={transactionMutation.isPending}
            transactions={transactions}
            currency={currency}
          />
          {categories.length === 0 && (
            <div className="finance-header-controls">
              <CurrencyControl
                currency={currency}
                error={settingsMutation.isError && !currencyConflict}
                feedback={currencyFeedback}
                locked={currencyLocked}
                pending={settingsMutation.isPending}
                onSave={(nextCurrency) => settingsMutation.mutateAsync(nextCurrency)}
              />
            </div>
          )}
        </div>
      </header>

      {isLoading ? (
        <StatusPanel kind="loading" title="Cargando el mes" description="Calculando movimientos y presupuestos." />
      ) : hasError ? (
        <StatusPanel
          action={<Button variant="secondary" onClick={() => void refreshFinance()}>Reintentar</Button>}
          kind="error"
          title="No pudimos cargar este mes"
          description="Conservamos el mes seleccionado. Inténtalo nuevamente."
        />
      ) : categories.length === 0 ? (
        <StatusPanel
          action={
            <CategoryDialog pending={categoryMutation.isPending} onSave={(input) => categoryMutation.mutateAsync({ input })}>
              <Button>Crear primera categoría</Button>
            </CategoryDialog>
          }
          kind="empty"
          title="Crea una categoría"
          description="Las categorías separan ingresos y gastos antes de registrar movimientos."
        />
      ) : (
        <>
          {summary && (
            <FinanceDashboard
              currency={currency}
              minorUnit={minorUnit}
              month={month}
              onMonthChange={setMonth}
              summaries={monthlySummaries}
              currencyControl={
                <CurrencyControl
                  currency={currency}
                  error={settingsMutation.isError && !currencyConflict}
                  feedback={currencyFeedback}
                  locked={currencyLocked}
                  pending={settingsMutation.isPending}
                  onSave={(nextCurrency) => settingsMutation.mutateAsync(nextCurrency)}
                />
              }
            />
          )}

          <section className="planner-section">
            <div className="section-heading">
              <div><span className="eyebrow">Organización y límites</span><h2>Categorías y presupuestos</h2></div>
              <CategoryDialog pending={categoryMutation.isPending} onSave={(input) => categoryMutation.mutateAsync({ input })}>
                <Button variant="secondary"><Plus aria-hidden="true" size={18} />Nueva categoría</Button>
              </CategoryDialog>
            </div>
            <div className="finance-management-list">
              {categories.map((category) => {
                const budget = budgets.find((item) => item.category_id === category.id);
                return (
                  <article className="finance-management-item" key={category.id}>
                    <div className="category-item">
                      <span className="category-dot" style={{ backgroundColor: category.color }} />
                      <div><strong>{category.name}</strong><small>{category.type === "income" ? "Ingreso" : "Gasto"}</small></div>
                      <CategoryDialog category={category} pending={categoryMutation.isPending} onSave={(input) => categoryMutation.mutateAsync({ id: category.id, input })}>
                        <button className="icon-button" aria-label={`Editar ${category.name}`}><Pencil aria-hidden="true" size={17} /></button>
                      </CategoryDialog>
                      <ConfirmDialog title="¿Archivar categoría?" description="Se conservarán sus movimientos y presupuestos históricos." onConfirm={() => archiveCategoryMutation.mutate(category.id)}>
                        <button className="icon-button" aria-label={`Archivar ${category.name}`}><Archive aria-hidden="true" size={17} /></button>
                      </ConfirmDialog>
                    </div>
                    {category.type === "expense" ? (
                      <BudgetRow
                        budgetMinor={budget?.limit_minor}
                        category={category}
                        currency={currency}
                        minorUnit={minorUnit}
                        pending={budgetMutation.isPending}
                        onDelete={budget ? () => deleteBudgetMutation.mutate(category.id) : undefined}
                        onSave={(limitMinor) => budgetMutation.mutateAsync({ categoryId: category.id, limitMinor })}
                      />
                    ) : (
                      <small className="finance-management-item__note">Los presupuestos aplican a categorías de gasto.</small>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
        </>
      )}

      {(categoryMutation.isError || transactionMutation.isError || budgetMutation.isError) && (
        <p className="inline-error" role="alert">No se pudo guardar. Revisa los datos e inténtalo nuevamente.</p>
      )}
    </FinanceFrame>
  );
}

function FinanceFrame({ children }: { children: ReactNode }) {
  return <div className="page page--wide">{children}</div>;
}

function FinanceCapture({
  categories,
  captureMode,
  currency,
  minorUnit,
  onCaptureModeChange,
  onConfirmed,
  onCreateCategory,
  onDeleteTransaction,
  onSaveExistingTransaction,
  onSaveTransaction,
  pending,
  transactions,
}: {
  categories: FinanceCategory[];
  captureMode: CaptureMode;
  currency: string;
  minorUnit: number;
  onCaptureModeChange: (mode: CaptureMode) => void;
  onConfirmed: () => Promise<void>;
  onCreateCategory: (input: CategoryInput) => Promise<FinanceCategory>;
  onDeleteTransaction: (id: number) => void;
  onSaveExistingTransaction: (id: number, input: TransactionInput) => Promise<unknown>;
  onSaveTransaction: (input: TransactionInput) => Promise<unknown>;
  pending: boolean;
  transactions: FinanceTransaction[];
}) {
  return (
    <details className="finance-capture">
      <summary>
        <span>
          <strong>Registrar tus gastos e ingresos</strong>
          <small>Elige si quieres registrar un movimiento o subir un documento.</small>
        </span>
        <ChevronDown aria-hidden="true" size={22} />
      </summary>
      <div className="finance-capture__content">
        <div className="finance-capture__choices" role="group" aria-label="Tipo de registro">
          <button
            className={captureMode === "manual" ? "finance-capture__choice finance-capture__choice--active" : "finance-capture__choice"}
            type="button"
            aria-pressed={captureMode === "manual"}
            onClick={() => onCaptureModeChange("manual")}
          >
            <strong>Manual</strong>
            <span>Registra un movimiento individual.</span>
          </button>
          <button
            className={captureMode === "automatic" ? "finance-capture__choice finance-capture__choice--active" : "finance-capture__choice"}
            type="button"
            aria-pressed={captureMode === "automatic"}
            onClick={() => onCaptureModeChange("automatic")}
          >
            <strong>Automático</strong>
            <span>Sube un recibo o extracto para revisarlo.</span>
          </button>
        </div>
        {captureMode === "automatic" ? (
          <FinanceImportPanel
            categories={categories}
            minorUnit={minorUnit}
            onConfirmed={onConfirmed}
            onCreateCategory={onCreateCategory}
          />
        ) : (
          <section className="planner-section">
            <div className="section-heading">
              <div><span className="eyebrow">Registro manual</span><h2>Movimientos</h2></div>
              <TransactionDialog
                categories={categories}
                minorUnit={minorUnit}
                pending={pending}
                onSave={onSaveTransaction}
              >
                <Button variant="secondary"><Plus aria-hidden="true" size={18} />Nuevo</Button>
              </TransactionDialog>
            </div>
            {transactions.length === 0 ? (
              <p className="empty-copy">Este mes aún no tiene movimientos.</p>
            ) : (
              <div className="data-list">
                {transactions.map((transaction) => (
                  <TransactionRow
                    categories={categories}
                    currency={currency}
                    key={transaction.id}
                    minorUnit={minorUnit}
                    transaction={transaction}
                    onDelete={() => onDeleteTransaction(transaction.id)}
                    onSave={(input) => onSaveExistingTransaction(transaction.id, input)}
                  />
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </details>
  );
}

function CurrencyOnboarding({
  error,
  onSave,
  pending,
}: {
  error: boolean;
  onSave: (currency: string) => void;
  pending: boolean;
}) {
  const [currency, setCurrency] = useState("COP");
  return (
    <section className="onboarding-panel">
      <span className="eyebrow">Configuración inicial</span>
      <h1>Elige tu moneda base</h1>
      <p>Se usará para todos los movimientos. Podrás cambiarla mientras no existan movimientos o presupuestos.</p>
      <div className="field">
        <label htmlFor="base-currency">Moneda</label>
        <select id="base-currency" value={currency} onChange={(event) => setCurrency(event.target.value)}>
          <option value="COP">COP — Peso colombiano</option>
          <option value="USD">USD — Dólar estadounidense</option>
          <option value="EUR">EUR — Euro</option>
        </select>
      </div>
      {error && <p className="inline-error" role="alert">No se pudo guardar la moneda. Inténtalo nuevamente.</p>}
      <Button disabled={pending} onClick={() => onSave(currency)}>{pending ? "Guardando…" : "Guardar moneda"}</Button>
    </section>
  );
}

function CurrencyControl({
  currency,
  error,
  feedback,
  locked,
  onSave,
  pending,
}: {
  currency: string;
  error: boolean;
  feedback: string;
  locked: boolean;
  onSave: (currency: string) => Promise<unknown>;
  pending: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [nextCurrency, setNextCurrency] = useState(currency);

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onSave(nextCurrency);
    setOpen(false);
  }

  if (locked) {
    return (
      <div className="currency-status">
        <strong>Moneda base: {currency}</strong>
        <small>
          Bloqueada porque existen movimientos o presupuestos. No se realiza conversión.
        </small>
      </div>
    );
  }

  return (
    <div className="currency-status">
      <span>Moneda base: {currency}</span>
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Trigger asChild>
          <Button variant="quiet">Editar moneda</Button>
        </Dialog.Trigger>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content dialog-content--small">
            <div className="dialog-heading">
              <div>
                <Dialog.Title>Editar moneda base</Dialog.Title>
                <Dialog.Description>
                  El cambio está disponible mientras no existan movimientos ni presupuestos.
                </Dialog.Description>
              </div>
              <Dialog.Close className="icon-button" aria-label="Cerrar">
                <X aria-hidden="true" size={20} />
              </Dialog.Close>
            </div>
            <form className="dialog-form" onSubmit={submit}>
              <div className="field">
                <label htmlFor="edit-base-currency">Moneda</label>
                <select
                  id="edit-base-currency"
                  value={nextCurrency}
                  onChange={(event) => setNextCurrency(event.target.value)}
                >
                  <option value="COP">COP — Peso colombiano</option>
                  <option value="USD">USD — Dólar estadounidense</option>
                  <option value="EUR">EUR — Euro</option>
                </select>
              </div>
              {error && (
                <p className="inline-error" role="alert">
                  No se pudo actualizar la moneda. Inténtalo nuevamente.
                </p>
              )}
              <div className="dialog-actions">
                <Button variant="secondary" onClick={() => setOpen(false)}>
                  Cancelar
                </Button>
                <Button disabled={pending} type="submit">
                  {pending ? "Guardando…" : "Guardar moneda"}
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
      {feedback && <small role="status">{feedback}</small>}
    </div>
  );
}

function FinanceDashboard({
  currency,
  currencyControl,
  minorUnit,
  month,
  onMonthChange,
  summaries,
}: {
  currency: string;
  currencyControl: ReactNode;
  minorUnit: number;
  month: string;
  onMonthChange: (month: string) => void;
  summaries: MonthlySummary[];
}) {
  const current = summaries[0];
  const periodExpense = summaries.reduce((total, item) => total + item.expense_minor, 0);
  const averageExpense = Math.round(periodExpense / Math.max(summaries.length, 1));
  const categoryTotals = new Map<string, { name: string; amount: number }>();
  summaries.forEach((summary) => {
    summary.categories
      .filter((category) => category.type === "expense")
      .forEach((category) => {
        const existing = categoryTotals.get(String(category.category_id));
        categoryTotals.set(String(category.category_id), {
          name: category.category_name,
          amount: (existing?.amount ?? 0) + category.actual_minor,
        });
      });
  });
  const categories = Array.from(categoryTotals.values())
    .filter((category) => category.amount > 0)
    .sort((left, right) => right.amount - left.amount);
  const highestMonthlyExpense = Math.max(...summaries.map((summary) => summary.expense_minor), 0);
  const periodLabel = summaries.length === 1 ? "Mes seleccionado" : `${summaries.length} meses`;
  const monthFormatter = new Intl.DateTimeFormat("es-CO", {
    month: "short",
    year: "numeric",
  });

  return (
    <section className="finance-dashboard" aria-label="Control financiero">
      <div className="finance-dashboard__heading">
        <div>
          <span className="eyebrow">Control financiero</span>
          <h2>Una lectura amplia de tus costos</h2>
          <p>Compara el mes seleccionado con los cinco meses anteriores y reconoce dónde se concentra el gasto.</p>
        </div>
        <div className="finance-dashboard__controls">
          <div className="finance-dashboard__month-control">
            <label htmlFor="finance-month">
              <span>Mes de referencia</span>
              <input id="finance-month" type="month" value={month} onChange={(event) => onMonthChange(event.target.value)} />
            </label>
            {currencyControl}
          </div>
          <span className="finance-dashboard__period">{periodLabel}</span>
        </div>
      </div>
      <div className="finance-dashboard__metrics">
        <article className="finance-dashboard__total">
          <span>Total gastado</span>
          <strong>{formatMoney(periodExpense, currency, minorUnit)}</strong>
          <small>{periodLabel} · promedio {formatMoney(averageExpense, currency, minorUnit)} al mes</small>
        </article>
        <article>
          <span>Gasto del mes</span>
          <strong>{formatMoney(current.expense_minor, currency, minorUnit)}</strong>
          <small>{current.month}</small>
        </article>
        <article>
          <span>Balance del mes</span>
          <strong>{formatMoney(current.balance_minor, currency, minorUnit)}</strong>
          <small>Ingresos menos gastos</small>
        </article>
        <article>
          <span>Presupuesto restante</span>
          <strong>{formatMoney(current.budget_remaining_minor, currency, minorUnit)}</strong>
          <small>Límite disponible del mes</small>
        </article>
      </div>
      <div className="finance-dashboard__grid">
        <section className="finance-dashboard__panel" aria-labelledby="finance-category-title">
          <div className="section-heading">
            <div><span className="eyebrow">Distribución</span><h3 id="finance-category-title">Categorías en el periodo</h3></div>
          </div>
          {categories.length === 0 ? (
            <p className="empty-copy">Aún no hay gastos categorizados en este periodo.</p>
          ) : (
            <div className="finance-dashboard__categories">
              {categories.map((category) => {
                const percentage = periodExpense
                  ? Math.round((category.amount / periodExpense) * 100)
                  : 0;
                return (
                  <div className="finance-dashboard__category" key={category.name}>
                    <div>
                      <strong>{category.name}</strong>
                      <small>{percentage} % del gasto · {formatMoney(category.amount, currency, minorUnit)}</small>
                    </div>
                    <progress max="100" value={percentage} aria-label={`${category.name}: ${percentage} %`} />
                  </div>
                );
              })}
            </div>
          )}
        </section>
        <section className="finance-dashboard__panel" aria-labelledby="finance-month-title">
          <div className="section-heading">
            <div><span className="eyebrow">Ritmo mensual</span><h3 id="finance-month-title">Gasto por mes</h3></div>
          </div>
          <div className="finance-dashboard__months">
            {summaries.map((summary, index) => {
              const percentage = highestMonthlyExpense
                ? Math.round((summary.expense_minor / highestMonthlyExpense) * 100)
                : 0;
              const date = new Date(`${summary.month}-01T12:00:00`);
              return (
                <div className="finance-dashboard__month" key={`${summary.month}-${index}`}>
                  <div>
                    <strong>{monthFormatter.format(date)}</strong>
                    <span>{formatMoney(summary.expense_minor, currency, minorUnit)}</span>
                  </div>
                  <progress max="100" value={percentage} aria-label={`${summary.month}: ${formatMoney(summary.expense_minor, currency, minorUnit)}`} />
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </section>
  );
}

function FormDialog({
  children,
  description,
  form,
  open,
  setOpen,
  title,
}: {
  children: ReactNode;
  description: string;
  form: ReactNode;
  open: boolean;
  setOpen: (open: boolean) => void;
  title: string;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{children}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-heading">
            <div><Dialog.Title>{title}</Dialog.Title><Dialog.Description>{description}</Dialog.Description></div>
            <Dialog.Close className="icon-button" aria-label="Cerrar"><X aria-hidden="true" size={20} /></Dialog.Close>
          </div>
          {form}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function CategoryDialog({
  category,
  children,
  onSave,
  pending,
}: {
  category?: FinanceCategory;
  children: ReactNode;
  onSave: (input: CategoryInput) => Promise<unknown>;
  pending: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(category?.name ?? "");
  const [type, setType] = useState<FinanceType>(category?.type ?? "expense");
  const [color, setColor] = useState(category?.color ?? categoryColors[0]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    await onSave({ name: name.trim(), type, color });
    setOpen(false);
  }
  return (
    <FormDialog
      open={open}
      setOpen={setOpen}
      title={category ? "Editar categoría" : "Crear categoría"}
      description="Define si agrupa ingresos o gastos."
      form={
        <form className="dialog-form" onSubmit={submit}>
          <div className="field"><label htmlFor={`category-name-${category?.id ?? "new"}`}>Nombre</label><input id={`category-name-${category?.id ?? "new"}`} maxLength={60} required value={name} onChange={(event) => setName(event.target.value)} /></div>
          <div className="field"><label htmlFor={`category-type-${category?.id ?? "new"}`}>Tipo</label><select id={`category-type-${category?.id ?? "new"}`} value={type} onChange={(event) => setType(event.target.value as FinanceType)}><option value="expense">Gasto</option><option value="income">Ingreso</option></select></div>
          <fieldset className="field fieldset"><legend>Color</legend><div className="color-picker">{categoryColors.map((value) => <label key={value}><input type="radio" name="category-color" checked={color === value} onChange={() => setColor(value)} /><span aria-label={value} style={{ backgroundColor: value }} /></label>)}</div></fieldset>
          <div className="dialog-actions"><Button variant="secondary" onClick={() => setOpen(false)}>Cancelar</Button><Button disabled={pending} type="submit">{pending ? "Guardando…" : "Guardar categoría"}</Button></div>
        </form>
      }
    >
      {children}
    </FormDialog>
  );
}

function TransactionDialog({
  categories,
  children,
  minorUnit,
  onSave,
  pending,
  transaction,
}: {
  categories: FinanceCategory[];
  children: ReactNode;
  minorUnit: number;
  onSave: (input: TransactionInput) => Promise<unknown>;
  pending?: boolean;
  transaction?: FinanceTransaction;
}) {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<FinanceType>(transaction?.type ?? "expense");
  const compatible = useMemo(() => categories.filter((category) => category.type === type), [categories, type]);
  const [amount, setAmount] = useState(transaction ? String(transaction.amount_minor / 10 ** minorUnit) : "");
  const [categoryId, setCategoryId] = useState(transaction?.category_id ?? 0);
  const [date, setDate] = useState(transaction?.date ?? toDateKey(new Date()));
  const [description, setDescription] = useState(transaction?.description ?? "");
  const [note, setNote] = useState(transaction?.note ?? "");
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    const amountMinor = parseMoney(amount, minorUnit);
    const selectedCategory = compatible.find((category) => category.id === categoryId) ?? compatible[0];
    if (!amountMinor || !selectedCategory) {
      setError("Ingresa un importe válido y elige una categoría compatible.");
      return;
    }
    await onSave({
      type,
      amount_minor: amountMinor,
      category_id: selectedCategory.id,
      date,
      description: description.trim(),
      note: note.trim() || null,
    });
    setOpen(false);
  }
  return (
    <FormDialog
      open={open}
      setOpen={setOpen}
      title={transaction ? "Editar movimiento" : "Registrar movimiento"}
      description="Los importes se guardan con la precisión de tu moneda."
      form={
        <form className="dialog-form" onSubmit={submit}>
          {error && <p className="form-error" role="alert" tabIndex={-1}>{error}</p>}
          <div className="field"><label htmlFor={`transaction-type-${transaction?.id ?? "new"}`}>Tipo</label><select id={`transaction-type-${transaction?.id ?? "new"}`} value={type} onChange={(event) => { setType(event.target.value as FinanceType); setCategoryId(0); }}><option value="expense">Gasto</option><option value="income">Ingreso</option></select></div>
          <div className="field"><label htmlFor={`transaction-amount-${transaction?.id ?? "new"}`}>Importe</label><input id={`transaction-amount-${transaction?.id ?? "new"}`} inputMode="decimal" placeholder={minorUnit === 0 ? "25000" : "250.00"} required value={amount} onChange={(event) => setAmount(event.target.value)} /></div>
          <div className="field"><label htmlFor={`transaction-category-${transaction?.id ?? "new"}`}>Categoría</label><select id={`transaction-category-${transaction?.id ?? "new"}`} required value={categoryId || compatible[0]?.id || ""} onChange={(event) => setCategoryId(Number(event.target.value))}>{compatible.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select>{compatible.length === 0 && <small className="field-help">Crea una categoría de este tipo antes de guardar.</small>}</div>
          <div className="field"><label htmlFor={`transaction-date-${transaction?.id ?? "new"}`}>Fecha</label><input id={`transaction-date-${transaction?.id ?? "new"}`} type="date" required value={date} onChange={(event) => setDate(event.target.value)} /></div>
          <div className="field"><label htmlFor={`transaction-description-${transaction?.id ?? "new"}`}>Descripción</label><input id={`transaction-description-${transaction?.id ?? "new"}`} maxLength={120} required value={description} onChange={(event) => setDescription(event.target.value)} /></div>
          <div className="field"><label htmlFor={`transaction-note-${transaction?.id ?? "new"}`}>Nota opcional</label><textarea id={`transaction-note-${transaction?.id ?? "new"}`} maxLength={500} rows={3} value={note} onChange={(event) => setNote(event.target.value)} /></div>
          <div className="dialog-actions"><Button variant="secondary" onClick={() => setOpen(false)}>Cancelar</Button><Button disabled={pending || compatible.length === 0} type="submit">{pending ? "Guardando…" : "Guardar movimiento"}</Button></div>
        </form>
      }
    >
      {children}
    </FormDialog>
  );
}

function TransactionRow({
  categories,
  currency,
  minorUnit,
  onDelete,
  onSave,
  transaction,
}: {
  categories: FinanceCategory[];
  currency: string;
  minorUnit: number;
  onDelete: () => void;
  onSave: (input: TransactionInput) => Promise<unknown>;
  transaction: FinanceTransaction;
}) {
  const category = categories.find((item) => item.id === transaction.category_id);
  return (
    <article className="data-row">
      <div><strong>{transaction.description}</strong><small>{transaction.date} · {category?.name ?? "Categoría archivada"}</small></div>
      <span className="money-value">{transaction.type === "expense" ? "−" : "+"}{formatMoney(transaction.amount_minor, currency, minorUnit)}</span>
      <TransactionDialog categories={categories} minorUnit={minorUnit} transaction={transaction} onSave={onSave}><button className="icon-button" aria-label={`Editar ${transaction.description}`}><Pencil aria-hidden="true" size={17} /></button></TransactionDialog>
      <ConfirmDialog confirmLabel="Eliminar" title="¿Eliminar movimiento?" description="Esta acción retirará el movimiento del resumen mensual." onConfirm={onDelete}><button className="icon-button" aria-label={`Eliminar ${transaction.description}`}><Trash2 aria-hidden="true" size={17} /></button></ConfirmDialog>
    </article>
  );
}

function BudgetRow({
  budgetMinor,
  category,
  currency,
  minorUnit,
  onDelete,
  onSave,
  pending,
}: {
  budgetMinor?: number;
  category: FinanceCategory;
  currency: string;
  minorUnit: number;
  onDelete?: () => void;
  onSave: (amount: number) => Promise<unknown>;
  pending: boolean;
}) {
  const [amount, setAmount] = useState(budgetMinor ? String(budgetMinor / 10 ** minorUnit) : "");
  const [error, setError] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    const parsed = parseMoney(amount, minorUnit);
    if (!parsed) {
      setError(true);
      return;
    }
    await onSave(parsed);
    setError(false);
  }
  return (
    <form className="budget-row" onSubmit={submit}>
      <div><strong>{category.name}</strong><small>{budgetMinor ? formatMoney(budgetMinor, currency, minorUnit) : "Sin presupuesto"}</small></div>
      <label className="sr-only" htmlFor={`budget-${category.id}`}>Límite para {category.name}</label>
      <input id={`budget-${category.id}`} inputMode="decimal" placeholder="Límite" value={amount} onChange={(event) => setAmount(event.target.value)} aria-invalid={error} />
      <Button disabled={pending} variant="secondary" type="submit">{budgetMinor ? "Actualizar" : "Configurar"}</Button>
      {onDelete && <button className="icon-button" type="button" aria-label={`Eliminar presupuesto de ${category.name}`} onClick={onDelete}><Trash2 aria-hidden="true" size={17} /></button>}
    </form>
  );
}
