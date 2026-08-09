import * as AlertDialog from "@radix-ui/react-alert-dialog";

import { Button } from "./Button";

interface ConfirmDialogProps {
  children: React.ReactNode;
  confirmLabel?: string;
  description: string;
  onConfirm: () => void;
  title: string;
}

export function ConfirmDialog({
  children,
  confirmLabel = "Archivar",
  description,
  onConfirm,
  title,
}: ConfirmDialogProps) {
  return (
    <AlertDialog.Root>
      <AlertDialog.Trigger asChild>{children}</AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="dialog-overlay" />
        <AlertDialog.Content className="dialog-content dialog-content--small">
          <AlertDialog.Title>{title}</AlertDialog.Title>
          <AlertDialog.Description>{description}</AlertDialog.Description>
          <div className="dialog-actions">
            <AlertDialog.Cancel asChild>
              <Button variant="secondary">Cancelar</Button>
            </AlertDialog.Cancel>
            <AlertDialog.Action asChild>
              <Button onClick={onConfirm} variant="danger">
                {confirmLabel}
              </Button>
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
