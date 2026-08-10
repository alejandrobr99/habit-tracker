import { Sprout } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useSession } from "../context/session-store";
import { ApiError } from "../lib/api";
import { OrganicMotif } from "../components/ui/OrganicMotif";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, notice, retry, status } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const user = await login(username, password);
      navigate(user.must_change_password ? "/cambiar-clave" : "/", {
        replace: true,
      });
    } catch (caughtError) {
      setPassword("");
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "No pudimos entrar. Inténtalo de nuevo.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <OrganicMotif className="auth-page__motif" variant="bloom" />
      <section aria-labelledby="login-title" className="auth-card">
        <div className="auth-brand" aria-hidden="true">
          <span className="brand__mark">
            <Sprout size={28} strokeWidth={1.7} />
          </span>
          <span>Pleno</span>
        </div>
        <span className="eyebrow">Tu espacio privado</span>
        <h1 id="login-title">Qué gusto verte</h1>
        <p className="auth-card__intro">
          Entra para continuar cuidando tus hábitos, progreso y finanzas.
        </p>

        {notice ? (
          <p className="auth-message auth-message--notice" role="status">
            {notice}
          </p>
        ) : null}
        {status === "error" ? (
          <button className="button button--secondary" onClick={() => void retry()}>
            Volver a comprobar
          </button>
        ) : null}

        <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
          <div className="field">
            <label htmlFor="username">Usuario</label>
            <input
              autoCapitalize="none"
              autoComplete="username"
              id="username"
              maxLength={40}
              onChange={(event) => setUsername(event.target.value)}
              required
              spellCheck={false}
              value={username}
            />
          </div>
          <div className="field">
            <label htmlFor="password">Contraseña</label>
            <input
              autoComplete="current-password"
              id="password"
              maxLength={128}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
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
            {isSubmitting ? "Entrando…" : "Entrar"}
          </button>
        </form>
        <p className="auth-card__footnote">
          Las cuentas se crean desde la administración de esta instancia.
        </p>
      </section>
    </main>
  );
}
