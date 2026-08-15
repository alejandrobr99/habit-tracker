import { FileUp, Plus, Save, Trash2 } from "lucide-react";
import { useMemo, useState, type ChangeEvent } from "react";

import { Button } from "../../components/ui/Button";
import { ApiError, plannerApi } from "../../lib/api";
import type {
  CategoryInput,
  FinanceCategory,
  OcrProposedTransaction,
  TransactionInput,
} from "../../types/planner";

const defaultCategoryColor = "#536B57";

type FinanceImportPanelProps = {
  categories: FinanceCategory[];
  minorUnit: number;
  onCreateCategory: (input: CategoryInput) => Promise<FinanceCategory>;
  onConfirmed: () => Promise<void>;
};

function formatAmount(row: OcrProposedTransaction, minorUnit: number): string {
  return row.amount_minor === null ? "" : String(row.amount_minor / 10 ** minorUnit);
}

export function FinanceImportPanel({
  categories,
  minorUnit,
  onCreateCategory,
  onConfirmed,
}: FinanceImportPanelProps) {
  const [preview, setPreview] = useState<{
    import_token: string;
    warnings: string[];
    rows: OcrProposedTransaction[];
  } | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [newCategory, setNewCategory] = useState<Record<string, string>>({});
  const categoryMap = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );

  async function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true);
    setStatus("");
    try {
      const result = await plannerApi.previewFinanceImport(file);
      setPreview(result);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setStatus("El presupuesto o el límite de análisis no está disponible.");
      } else if (error instanceof ApiError && error.status === 503) {
        setStatus("El servicio OCR está temporalmente no disponible. Inténtalo de nuevo.");
      } else if (error instanceof ApiError && error.status === 422) {
        setStatus(error.message);
      } else {
        setStatus("No pudimos interpretar la respuesta del OCR. Inténtalo de nuevo.");
      }
    } finally {
      setBusy(false);
    }
  }

  function updateRow(rowId: string, changes: Partial<OcrProposedTransaction>) {
    setPreview((current) =>
      current
        ? { ...current, rows: current.rows.map((row) => row.row_id === rowId ? { ...row, ...changes } : row) }
        : current,
    );
  }

  function removeRow(rowId: string) {
    setPreview((current) =>
      current
        ? { ...current, rows: current.rows.filter((row) => row.row_id !== rowId) }
        : current,
    );
  }

  async function createCategory(row: OcrProposedTransaction) {
    const name = newCategory[row.row_id]?.trim();
    if (!name) return;
    setBusy(true);
    try {
      const category = await onCreateCategory({
        name,
        type: row.type,
        color: defaultCategoryColor,
      });
      updateRow(row.row_id, { category_id: category.id, category_name: category.name, field_errors: {} });
      setNewCategory((current) => ({ ...current, [row.row_id]: "" }));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!preview) return;
    const rows: TransactionInput[] = preview.rows.map((row) => ({
      type: row.type,
      amount_minor: row.amount_minor ?? 0,
      category_id: row.category_id ?? 0,
      date: row.date ?? "",
      description: row.description ?? "",
      note: null,
    }));
    if (rows.some((row) => !row.amount_minor || !row.category_id || !row.date || !row.description)) {
      setStatus("Completa los campos marcados antes de confirmar.");
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      await plannerApi.confirmFinanceImport(preview.import_token, rows);
      setPreview(null);
      await onConfirmed();
      setStatus("Importación confirmada. Los movimientos y el resumen fueron actualizados.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setStatus("La revisión expiró. Vuelve a importar el documento.");
      } else if (error instanceof ApiError && error.status === 409) {
        setStatus(error.message);
      } else if (error instanceof ApiError && error.status === 422) {
        setStatus("Hay campos inválidos. Revisa las filas antes de confirmar.");
      } else {
        setStatus("No se pudo confirmar. No se guardó ninguna fila.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="planner-section finance-import" aria-label="Importar documento financiero">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Registro automático</span>
          <h2>Importar recibo o extracto</h2>
        </div>
        {!preview && (
          <label className="button button--primary">
            <FileUp aria-hidden="true" size={18} />
            {busy ? "Analizando…" : "Elegir documento"}
            <input
              accept="image/jpeg,image/png,application/pdf"
              className="sr-only"
              disabled={busy}
              onChange={selectFile}
              type="file"
            />
          </label>
        )}
      </div>
      <p className="field-help finance-import__instructions">
        Se envía una copia temporal a Google Gemini. Usa JPEG, PNG o PDF de hasta 10 MiB. Revisa cada
        fila: el OCR nunca guarda movimientos automáticamente.
      </p>
      {status && <p className="inline-error" role="status">{status}</p>}
      {preview && (
        <>
          {preview.warnings.map((warning) => <p className="field-help" key={warning}>{warning}</p>)}
          <div className="finance-import-table" role="table" aria-label="Propuestas editables">
            <div className="finance-import-row finance-import-row--header" role="row">
              <strong>Fecha</strong>
              <strong>Descripción</strong>
              <strong>Valor de transacción</strong>
              <strong>Categoría</strong>
              <strong>Acción</strong>
            </div>
            {preview.rows.map((row) => {
              const category = row.category_id ? categoryMap.get(row.category_id) : undefined;
              return (
                <div className="finance-import-row" key={row.row_id} role="row">
                  <label>
                    <span className="sr-only">Fecha</span>
                    <input
                      aria-invalid={Boolean(row.field_errors.date)}
                      type="date"
                      value={row.date ?? ""}
                      onChange={(event) => updateRow(row.row_id, { date: event.target.value })}
                    />
                  </label>
                  <label>
                    <span className="sr-only">Descripción</span>
                    <input
                      aria-invalid={Boolean(row.field_errors.description)}
                      maxLength={120}
                      value={row.description ?? ""}
                      onChange={(event) => updateRow(row.row_id, { description: event.target.value })}
                    />
                  </label>
                  <label>
                    <span className="sr-only">Valor de transacción</span>
                    <input
                      aria-invalid={Boolean(row.field_errors.amount_minor)}
                      inputMode="decimal"
                      value={formatAmount(row, minorUnit)}
                      onChange={(event) => {
                        const normalized = event.target.value.replace(",", ".");
                        const parsed = Number(normalized);
                        updateRow(row.row_id, {
                          amount_minor: Number.isFinite(parsed) && parsed > 0
                            ? Math.round(parsed * 10 ** minorUnit)
                            : null,
                        });
                      }}
                    />
                  </label>
                  <label>
                    <span className="sr-only">Categoría</span>
                    <select
                      aria-invalid={Boolean(row.field_errors.category_id)}
                      value={row.category_id ?? ""}
                      onChange={(event) => {
                        const selected = categoryMap.get(Number(event.target.value));
                        updateRow(row.row_id, {
                          category_id: selected?.id ?? null,
                          category_name: selected?.name ?? null,
                        });
                      }}
                    >
                      <option value="">Elegir categoría</option>
                      {categories
                        .filter((item) => item.type === row.type)
                        .map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                    {category ? null : (
                      <span className="finance-import-new-category">
                        <input
                          aria-label={`Nueva categoría para fila ${row.row_id}`}
                          placeholder="Nueva categoría"
                          value={newCategory[row.row_id] ?? ""}
                          onChange={(event) => setNewCategory((current) => ({ ...current, [row.row_id]: event.target.value }))}
                        />
                        <Button
                          aria-label="Crear categoría"
                          disabled={busy || !newCategory[row.row_id]?.trim()}
                          onClick={() => void createCategory(row)}
                          type="button"
                          variant="quiet"
                        >
                          <Plus aria-hidden="true" size={16} />
                        </Button>
                      </span>
                    )}
                  </label>
                  <Button
                    aria-label={`Eliminar fila ${row.row_id}`}
                    disabled={busy}
                    onClick={() => removeRow(row.row_id)}
                    type="button"
                    variant="quiet"
                  >
                    <Trash2 aria-hidden="true" size={17} />
                  </Button>
                </div>
              );
            })}
          </div>
          {preview.rows.length === 0 && (
            <p className="field-help">No quedan filas para confirmar. Puedes importar otro documento.</p>
          )}
          <div className="dialog-actions">
            <Button onClick={() => setPreview(null)} variant="secondary">Cancelar</Button>
            <Button disabled={busy || preview.rows.length === 0} onClick={() => void confirm()}>
              <Save aria-hidden="true" size={17} />
              {busy ? "Confirmando…" : "Confirmar importación"}
            </Button>
          </div>
        </>
      )}
    </section>
  );
}

