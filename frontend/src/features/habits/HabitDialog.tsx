import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useId,
  useState,
} from "react";

import { Button } from "../../components/ui/Button";
import type { Habit, HabitInput } from "../../types/planner";

const colors = [
  { name: "Salvia", value: "#71806d" },
  { name: "Terracota", value: "#b66b52" },
  { name: "Azul tinta", value: "#52677a" },
  { name: "Mostaza", value: "#a98445" },
];

const emptyHabit: HabitInput = {
  name: "",
  description: null,
  frequency: "daily",
  color: colors[0].value,
};

interface HabitDialogProps {
  children: ReactNode;
  habit?: Habit;
  isPending?: boolean;
  onSave: (input: HabitInput) => Promise<void>;
}

export function HabitDialog({
  children,
  habit,
  isPending = false,
  onSave,
}: HabitDialogProps) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<HabitInput>(emptyHabit);
  const nameId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (open) {
      setForm(
        habit
          ? {
              name: habit.name,
              description: habit.description,
              frequency: habit.frequency,
              color: habit.color,
            }
          : emptyHabit,
      );
    }
  }, [habit, open]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSave({
      ...form,
      name: form.name.trim(),
      description: form.description?.trim() || null,
    });
    setOpen(false);
  }

  return (
    <Dialog.Root onOpenChange={setOpen} open={open}>
      <Dialog.Trigger asChild>{children}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-heading">
            <div>
              <Dialog.Title>
                {habit ? "Editar hábito" : "Crear un hábito"}
              </Dialog.Title>
              <Dialog.Description>
                Define una intención concreta y fácil de registrar.
              </Dialog.Description>
            </div>
            <Dialog.Close aria-label="Cerrar" className="icon-button">
              <X aria-hidden="true" size={20} />
            </Dialog.Close>
          </div>

          <form className="habit-form" onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor={nameId}>Nombre</label>
              <input
                autoFocus
                id={nameId}
                maxLength={80}
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
                placeholder="Ej. Caminar después de comer"
                required
                value={form.name}
              />
            </div>

            <div className="field">
              <label htmlFor={descriptionId}>Nota breve</label>
              <textarea
                id={descriptionId}
                maxLength={240}
                onChange={(event) =>
                  setForm({ ...form, description: event.target.value })
                }
                placeholder="Por qué quieres mantenerlo"
                rows={3}
                value={form.description ?? ""}
              />
            </div>

            <fieldset className="field fieldset">
              <legend>Frecuencia</legend>
              <div className="segmented">
                {(["daily", "weekly"] as const).map((frequency) => (
                  <label key={frequency}>
                    <input
                      checked={form.frequency === frequency}
                      name="frequency"
                      onChange={() => setForm({ ...form, frequency })}
                      type="radio"
                      value={frequency}
                    />
                    <span>{frequency === "daily" ? "Diario" : "Semanal"}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <fieldset className="field fieldset">
              <legend>Color</legend>
              <div className="color-picker">
                {colors.map((color) => (
                  <label key={color.value} title={color.name}>
                    <input
                      checked={form.color === color.value}
                      name="color"
                      onChange={() => setForm({ ...form, color: color.value })}
                      type="radio"
                      value={color.value}
                    />
                    <span
                      aria-label={color.name}
                      style={{ backgroundColor: color.value }}
                    />
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="dialog-actions">
              <Dialog.Close asChild>
                <Button variant="secondary">Cancelar</Button>
              </Dialog.Close>
              <Button disabled={isPending} type="submit">
                {isPending
                  ? "Guardando…"
                  : habit
                    ? "Guardar cambios"
                    : "Crear hábito"}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
