import { AlertCircle, Inbox, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

type StatusKind = "empty" | "error" | "loading";

interface StatusPanelProps {
  action?: ReactNode;
  description: string;
  kind: StatusKind;
  title: string;
}

const icons = {
  empty: Inbox,
  error: AlertCircle,
  loading: LoaderCircle,
};

export function StatusPanel({
  action,
  description,
  kind,
  title,
}: StatusPanelProps) {
  const Icon = icons[kind];
  return (
    <div className="status-panel" role={kind === "error" ? "alert" : "status"}>
      <Icon
        aria-hidden="true"
        className={kind === "loading" ? "status-panel__spinner" : ""}
        size={22}
      />
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
