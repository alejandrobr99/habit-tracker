import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, ShieldCheck, UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";

import { ApiError, plannerApi } from "../lib/api";
import type {
  PlannerUser,
  UserRole,
  UserStatus,
} from "../types/planner";

interface UserUpdate {
  display_name?: string;
  role?: UserRole;
  status?: UserStatus;
}

export function AdminPage() {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<PlannerUser | null>(null);

  const usersQuery = useQuery({
    queryKey: ["admin-users"],
    queryFn: plannerApi.listUsers,
  });
  const createMutation = useMutation({
    mutationFn: plannerApi.createUser,
    onSuccess: async () => {
      setFeedback("Cuenta creada. Comparte la contraseña temporal de forma privada.");
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: UserUpdate }) =>
      plannerApi.updateUser(id, input),
    onSuccess: async () => {
      setFeedback("Cambios guardados.");
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
  const resetMutation = useMutation({
    mutationFn: ({
      id,
      temporaryPassword,
    }: {
      id: number;
      temporaryPassword: string;
    }) => plannerApi.resetUserPassword(id, temporaryPassword),
    onSuccess: async () => {
      setResetTarget(null);
      setFeedback("Contraseña temporal actualizada y sesiones cerradas.");
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  const mutationError =
    createMutation.error ?? updateMutation.error ?? resetMutation.error;
  const errorMessage =
    mutationError instanceof ApiError
      ? mutationError.message
      : mutationError
        ? "No pudimos completar el cambio."
        : null;

  return (
    <div className="page page--wide">
      <header className="page-header">
        <div>
          <span className="eyebrow">Acceso privado</span>
          <h1>Administración</h1>
          <p>
            Crea y cuida las cuentas de esta instancia. Ser administrador no
            permite ver hábitos, finanzas ni progreso ajenos.
          </p>
        </div>
        <span className="admin-header__icon">
          <ShieldCheck aria-hidden="true" size={30} />
        </span>
      </header>

      {feedback ? (
        <p className="auth-message auth-message--success" role="status">
          {feedback}
        </p>
      ) : null}
      {errorMessage ? (
        <p className="form-error" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <section aria-labelledby="new-user-title" className="admin-panel">
        <div className="admin-panel__heading">
          <UserPlus aria-hidden="true" size={24} />
          <div>
            <h2 id="new-user-title">Nueva cuenta</h2>
            <p>La persona elegirá su propia contraseña al entrar.</p>
          </div>
        </div>
        <CreateUserForm
          isSubmitting={createMutation.isPending}
          onSubmit={(input) => {
            setFeedback(null);
            createMutation.mutate(input);
          }}
        />
      </section>

      <section aria-labelledby="users-title" className="admin-panel">
        <div className="admin-panel__heading">
          <ShieldCheck aria-hidden="true" size={24} />
          <div>
            <h2 id="users-title">Cuentas</h2>
            <p>Desactivar o restablecer una cuenta cierra sus sesiones.</p>
          </div>
        </div>
        {usersQuery.isLoading ? (
          <p aria-live="polite">Cargando cuentas…</p>
        ) : usersQuery.isError ? (
          <div className="status-panel">
            <p>No pudimos cargar las cuentas.</p>
            <button
              className="button button--secondary"
              onClick={() => void usersQuery.refetch()}
              type="button"
            >
              Reintentar
            </button>
          </div>
        ) : (
          <div className="admin-users">
            {usersQuery.data?.map((user) => (
              <UserAccount
                isSaving={updateMutation.isPending}
                key={user.id}
                onReset={() => setResetTarget(user)}
                onUpdate={(input) => {
                  setFeedback(null);
                  updateMutation.mutate({ id: user.id, input });
                }}
                user={user}
              />
            ))}
          </div>
        )}
      </section>

      {resetTarget ? (
        <ResetPasswordPanel
          isSubmitting={resetMutation.isPending}
          onCancel={() => setResetTarget(null)}
          onSubmit={(temporaryPassword) => {
            setFeedback(null);
            resetMutation.mutate({
              id: resetTarget.id,
              temporaryPassword,
            });
          }}
          user={resetTarget}
        />
      ) : null}
    </div>
  );
}

function CreateUserForm({
  isSubmitting,
  onSubmit,
}: {
  isSubmitting: boolean;
  onSubmit: (input: {
    username: string;
    display_name: string;
    temporary_password: string;
    role: UserRole;
  }) => void;
}) {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [role, setRole] = useState<UserRole>("member");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      username,
      display_name: displayName,
      temporary_password: temporaryPassword,
      role,
    });
  }

  return (
    <form className="admin-create-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="new-display-name">Nombre visible</label>
        <input
          id="new-display-name"
          maxLength={80}
          onChange={(event) => setDisplayName(event.target.value)}
          required
          value={displayName}
        />
      </div>
      <div className="field">
        <label htmlFor="new-username">Usuario</label>
        <input
          autoCapitalize="none"
          id="new-username"
          maxLength={40}
          minLength={3}
          onChange={(event) => setUsername(event.target.value.toLowerCase())}
          pattern="[a-z0-9._-]+"
          required
          spellCheck={false}
          value={username}
        />
      </div>
      <div className="field">
        <label htmlFor="temporary-password">Contraseña temporal</label>
        <input
          autoComplete="new-password"
          id="temporary-password"
          maxLength={128}
          minLength={12}
          onChange={(event) => setTemporaryPassword(event.target.value)}
          required
          type="password"
          value={temporaryPassword}
        />
      </div>
      <div className="field">
        <label htmlFor="new-role">Rol</label>
        <select
          id="new-role"
          onChange={(event) => setRole(event.target.value as UserRole)}
          value={role}
        >
          <option value="member">Miembro</option>
          <option value="admin">Administrador</option>
        </select>
      </div>
      <button
        className="button button--primary"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? "Creando…" : "Crear cuenta"}
      </button>
    </form>
  );
}

function UserAccount({
  isSaving,
  onReset,
  onUpdate,
  user,
}: {
  isSaving: boolean;
  onReset: () => void;
  onUpdate: (input: UserUpdate) => void;
  user: PlannerUser;
}) {
  const [displayName, setDisplayName] = useState(user.display_name);

  return (
    <article className="admin-user">
      <div className="admin-user__identity">
        <div>
          <strong>{user.display_name}</strong>
          <span>@{user.username}</span>
        </div>
        <span
          className={`status-pill status-pill--${user.status}`}
        >
          {user.status === "active" ? "Activa" : "Desactivada"}
        </span>
      </div>
      <div className="admin-user__controls">
        <div className="field">
          <label htmlFor={`display-name-${user.id}`}>Nombre visible</label>
          <input
            id={`display-name-${user.id}`}
            maxLength={80}
            onChange={(event) => setDisplayName(event.target.value)}
            value={displayName}
          />
        </div>
        <div className="field">
          <label htmlFor={`role-${user.id}`}>Rol</label>
          <select
            id={`role-${user.id}`}
            onChange={(event) =>
              onUpdate({ role: event.target.value as UserRole })
            }
            value={user.role}
          >
            <option value="member">Miembro</option>
            <option value="admin">Administrador</option>
          </select>
        </div>
      </div>
      <div className="admin-user__actions">
        <button
          className="button button--secondary"
          disabled={isSaving || displayName.trim() === user.display_name}
          onClick={() => onUpdate({ display_name: displayName.trim() })}
          type="button"
        >
          Guardar nombre
        </button>
        <button
          className="button button--secondary"
          onClick={onReset}
          type="button"
        >
          <KeyRound aria-hidden="true" size={18} />
          Restablecer clave
        </button>
        <button
          className="text-button"
          onClick={() =>
            onUpdate({
              status: user.status === "active" ? "disabled" : "active",
            })
          }
          type="button"
        >
          {user.status === "active" ? "Desactivar" : "Reactivar"}
        </button>
      </div>
    </article>
  );
}

function ResetPasswordPanel({
  isSubmitting,
  onCancel,
  onSubmit,
  user,
}: {
  isSubmitting: boolean;
  onCancel: () => void;
  onSubmit: (temporaryPassword: string) => void;
  user: PlannerUser;
}) {
  const [temporaryPassword, setTemporaryPassword] = useState("");

  return (
    <section aria-labelledby="reset-title" className="admin-panel admin-reset">
      <div className="admin-panel__heading">
        <KeyRound aria-hidden="true" size={24} />
        <div>
          <h2 id="reset-title">Nueva clave temporal</h2>
          <p>
            Para {user.display_name}. Sus sesiones actuales se cerrarán.
          </p>
        </div>
      </div>
      <form
        className="admin-reset__form"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit(temporaryPassword);
        }}
      >
        <div className="field">
          <label htmlFor="reset-password">Contraseña temporal</label>
          <input
            autoComplete="new-password"
            id="reset-password"
            maxLength={128}
            minLength={12}
            onChange={(event) => setTemporaryPassword(event.target.value)}
            required
            type="password"
            value={temporaryPassword}
          />
        </div>
        <div className="admin-reset__actions">
          <button
            className="button button--primary"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Guardando…" : "Guardar clave"}
          </button>
          <button
            className="button button--secondary"
            onClick={onCancel}
            type="button"
          >
            Cancelar
          </button>
        </div>
      </form>
    </section>
  );
}
