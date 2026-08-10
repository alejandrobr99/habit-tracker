import { KeyRound, Sprout } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useSession } from "../context/session-store";
import { ApiError } from "../lib/api";

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const { changePassword, logout, user } = useSession();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (newPassword !== confirmation) {
      setError("Las contraseñas nuevas no coinciden.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      navigate("/", { replace: true });
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "No pudimos cambiar la contraseña.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section aria-labelledby="password-title" className="auth-card">
        <div className="auth-brand">
          <span className="brand__mark">
            <Sprout aria-hidden="true" size={28} strokeWidth={1.7} />
          </span>
          <span>Pleno</span>
        </div>
        <span className="eyebrow">Primer paso de seguridad</span>
        <h1 id="password-title">Elige tu contraseña</h1>
        <p className="auth-card__intro">
          Hola, {user?.display_name}. Cambia la contraseña temporal antes de
          abrir tu espacio privado.
        </p>
        <div className="auth-security-note">
          <KeyRound aria-hidden="true" size={22} />
          <p>Usa al menos 12 caracteres. Una frase larga es fácil de recordar.</p>
        </div>
        <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
          <div className="field">
            <label htmlFor="current-password">Contraseña temporal</label>
            <input
              autoComplete="current-password"
              id="current-password"
              maxLength={128}
              onChange={(event) => setCurrentPassword(event.target.value)}
              required
              type="password"
              value={currentPassword}
            />
          </div>
          <div className="field">
            <label htmlFor="new-password">Nueva contraseña</label>
            <input
              autoComplete="new-password"
              id="new-password"
              maxLength={128}
              minLength={12}
              onChange={(event) => setNewPassword(event.target.value)}
              required
              type="password"
              value={newPassword}
            />
          </div>
          <div className="field">
            <label htmlFor="password-confirmation">Repite la nueva contraseña</label>
            <input
              autoComplete="new-password"
              id="password-confirmation"
              maxLength={128}
              minLength={12}
              onChange={(event) => setConfirmation(event.target.value)}
              required
              type="password"
              value={confirmation}
            />
          </div>
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
          <button
            className="button button--primary auth-form__submit"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Guardando…" : "Guardar y continuar"}
          </button>
        </form>
        <button
          className="text-button auth-card__logout"
          onClick={() => void logout()}
          type="button"
        >
          Salir de esta cuenta
        </button>
      </section>
    </main>
  );
}
