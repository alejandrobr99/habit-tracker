import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Award, Gift, Pencil, Plus, X } from "lucide-react";
import {
  type FormEvent,
  type ReactNode,
  useState,
} from "react";

import { Button } from "../components/ui/Button";
import { Celebration } from "../components/ui/Celebration";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { OrganicMotif } from "../components/ui/OrganicMotif";
import { StatusPanel } from "../components/ui/StatusPanel";
import { ApiError, plannerApi } from "../lib/api";
import { startOfWeek, toDateKey } from "../lib/date";
import type { Habit, Reward, RewardInput } from "../types/planner";

export function ProgressPage() {
  const weekStart = toDateKey(startOfWeek());
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<{
    description: string;
    kind: "milestone" | "reward" | "routine";
    title: string;
  } | null>(null);
  const progressQuery = useQuery({
    queryKey: ["progress"],
    queryFn: plannerApi.getProgress,
  });
  const badgesQuery = useQuery({
    queryKey: ["badges"],
    queryFn: plannerApi.listBadges,
  });
  const habitsQuery = useQuery({
    queryKey: ["habits"],
    queryFn: plannerApi.listHabits,
  });
  const challengeQuery = useQuery({
    queryKey: ["weekly-challenge", weekStart],
    queryFn: () => plannerApi.getWeeklyChallenge(weekStart),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
  const rewardsQuery = useQuery({
    queryKey: ["rewards"],
    queryFn: () => plannerApi.listRewards(),
  });

  async function refreshProgress() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["progress"] }),
      queryClient.invalidateQueries({ queryKey: ["badges"] }),
      queryClient.invalidateQueries({ queryKey: ["weekly-challenge"] }),
      queryClient.invalidateQueries({ queryKey: ["rewards"] }),
    ]);
  }

  const challengeMutation = useMutation({
    mutationFn: ({
      habitId,
      targetCount,
    }: {
      habitId: number | null;
      targetCount: number;
    }) => plannerApi.createWeeklyChallenge({
      week_start: weekStart,
      habit_id: habitId,
      target_count: targetCount,
    }),
    onSuccess: async () => {
      setFeedback({
        description: "Puedes seguir su avance aquí durante la semana.",
        kind: "routine",
        title: "Desafío semanal creado",
      });
      await refreshProgress();
    },
  });
  const deleteChallengeMutation = useMutation({
    mutationFn: plannerApi.deleteWeeklyChallenge,
    onSuccess: async () => {
      setFeedback({
        description: "Tus registros y XP anteriores se conservaron.",
        kind: "routine",
        title: "Desafío eliminado",
      });
      await refreshProgress();
    },
  });
  const rewardMutation = useMutation({
    mutationFn: ({ id, input }: { id?: number; input: RewardInput }) =>
      id ? plannerApi.updateReward(id, input) : plannerApi.createReward(input),
    onSuccess: async () => {
      setFeedback({
        description: "Quedó disponible como una elección personal.",
        kind: "routine",
        title: "Recompensa guardada",
      });
      await refreshProgress();
    },
  });
  const archiveRewardMutation = useMutation({
    mutationFn: plannerApi.archiveReward,
    onSuccess: refreshProgress,
  });
  const redeemMutation = useMutation({
    mutationFn: (rewardId: number) =>
      plannerApi.redeemReward(rewardId, crypto.randomUUID()),
    onSuccess: async (_, rewardId) => {
      const reward = rewardsQuery.data?.find((item) => item.id === rewardId);
      setFeedback({
        description: "Este momento lo elegiste tú. Disfrútalo a tu manera.",
        kind: "reward",
        title: reward?.name ?? "Recompensa canjeada",
      });
      await refreshProgress();
    },
  });
  const reviewMutation = useMutation({
    mutationFn: () => plannerApi.putFinanceReview(weekStart),
    onSuccess: async () => {
      setFeedback({
        description: "Tu revisión quedó reconocida sin valorar montos ni resultados.",
        kind: "milestone",
        title: "Revisión semanal completada",
      });
      await refreshProgress();
    },
  });

  const challengeMissing = challengeQuery.error instanceof ApiError
    && challengeQuery.error.status === 404;
  const isLoading = progressQuery.isLoading
    || badgesQuery.isLoading
    || habitsQuery.isLoading
    || rewardsQuery.isLoading
    || challengeQuery.isLoading;
  const hasError = progressQuery.isError
    || badgesQuery.isError
    || habitsQuery.isError
    || rewardsQuery.isError
    || (challengeQuery.isError && !challengeMissing);

  if (isLoading) {
    return (
      <ProgressFrame>
        <StatusPanel
          kind="loading"
          title="Cargando progreso"
          description="Preparando nivel, insignias y elecciones personales."
        />
      </ProgressFrame>
    );
  }
  if (hasError || !progressQuery.data) {
    return (
      <ProgressFrame>
        <StatusPanel
          action={<Button variant="secondary" onClick={() => void refreshProgress()}>Reintentar</Button>}
          kind="error"
          title="No pudimos cargar tu progreso"
          description="Revisa que la API esté disponible e inténtalo nuevamente."
        />
      </ProgressFrame>
    );
  }

  const progress = progressQuery.data;
  const levelProgress = progress.next_level_xp === progress.level_start_xp
    ? 0
    : (
        (progress.lifetime_xp - progress.level_start_xp)
        / (progress.next_level_xp - progress.level_start_xp)
      ) * 100;
  const challenge = challengeQuery.data;
  const rewards = rewardsQuery.data ?? [];
  const habits = habitsQuery.data ?? [];

  return (
    <ProgressFrame>
      <header className="page-header">
        <div>
          <span className="eyebrow">Progreso privado</span>
          <h1>Progreso</h1>
          <p>Un contexto opcional para reconocer acciones que elegiste.</p>
        </div>
        <RewardDialog
          pending={rewardMutation.isPending}
          onSave={(input) => rewardMutation.mutateAsync({ input })}
        >
          <Button><Plus aria-hidden="true" size={18} />Crear recompensa</Button>
        </RewardDialog>
      </header>

      {feedback && (
        feedback.kind === "routine" ? (
          <div className="achievement-feedback" role="status">
            <Award aria-hidden="true" size={20} />
            <span>
              <strong>{feedback.title}</strong>
              {" "}
              {feedback.description}
            </span>
            <button
              className="text-button"
              onClick={() => setFeedback(null)}
              type="button"
            >
              Cerrar
            </button>
          </div>
        ) : (
          <Celebration
            description={feedback.description}
            kind={feedback.kind}
            onDismiss={() => setFeedback(null)}
            title={feedback.title}
          />
        )
      )}

      <section className="progress-hero" aria-label={`Nivel ${progress.level}`}>
        <div className="level-emblem">
          <div>
            <span>Nivel</span>
            <strong>{progress.level}</strong>
          </div>
        </div>
        <div className="level-details">
          <span className="eyebrow">Tu recorrido</span>
          <h2>Lo que has elegido sostener</h2>
          <span>
            {progress.lifetime_xp} XP acumulado · {progress.available_xp} XP disponible
          </span>
          <progress
            aria-label={`${Math.round(levelProgress)}% hacia el siguiente nivel`}
            max={100}
            value={Math.max(0, Math.min(100, levelProgress))}
          />
          <small>
            {progress.next_level_xp - progress.lifetime_xp} XP para el siguiente nivel
          </small>
        </div>
        <OrganicMotif className="progress-hero__motif" variant="orbit" />
      </section>

      <section className="planner-section">
        <div className="section-heading"><div><span className="eyebrow">Esta semana</span><h2>Desafío elegido</h2></div></div>
        {challenge ? (
          <article className="challenge-panel">
            <div>
              <strong>{challenge.progress_count} de {challenge.target_count} avances</strong>
              <p>
                {challenge.status === "expired"
                  ? "La semana terminó."
                  : challenge.status === "completed"
                    ? "Desafío completado."
                    : "Desafío activo para esta semana."}
              </p>
            </div>
            <progress max={challenge.target_count} value={challenge.progress_count} />
            {challenge.status === "active" && (
              <ConfirmDialog
                confirmLabel="Eliminar"
                title="¿Eliminar desafío?"
                description="El progreso de hábitos se conserva y no se resta XP."
                onConfirm={() => deleteChallengeMutation.mutate(challenge.id)}
              >
                <Button variant="secondary">Eliminar desafío</Button>
              </ConfirmDialog>
            )}
          </article>
        ) : (
          <ChallengeForm
            habits={habits}
            pending={challengeMutation.isPending}
            onSave={(habitId, targetCount) => challengeMutation.mutate({ habitId, targetCount })}
          />
        )}
      </section>

      <section className="planner-section">
        <div className="section-heading"><div><span className="eyebrow">Reconocimientos</span><h2>Insignias</h2></div></div>
        <div className="badge-grid">
          {(badgesQuery.data ?? []).map((badge) => (
            <article
              className={badge.awarded ? "badge-item badge-item--awarded" : "badge-item"}
              key={badge.code}
            >
              <Award aria-hidden="true" size={21} />
              <div>
                <strong>{badge.name}</strong>
                <p>{badge.description}</p>
                <small>{badge.awarded ? "Obtenida" : "Pendiente"}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="planner-section">
        <div className="section-heading">
          <div><span className="eyebrow">Elecciones personales</span><h2>Recompensas</h2></div>
          <RewardDialog pending={rewardMutation.isPending} onSave={(input) => rewardMutation.mutateAsync({ input })}>
            <Button variant="secondary"><Plus aria-hidden="true" size={18} />Nueva</Button>
          </RewardDialog>
        </div>
        {rewards.length === 0 ? (
          <p className="empty-copy">Crea una recompensa personal cuando te resulte útil.</p>
        ) : (
          <div className="reward-grid">
            {rewards.map((reward) => (
              <article className="reward-card" key={reward.id}>
                <span className="reward-card__icon">
                  <Gift aria-hidden="true" size={21} />
                </span>
                <div className="reward-card__content">
                  <h3>{reward.name}</h3>
                  <p>{reward.description || "Una elección personal para disfrutar."}</p>
                  <span className="reward-card__cost">{reward.cost_xp} XP</span>
                </div>
                <div className="reward-card__actions">
                  <Button
                    disabled={
                      redeemMutation.isPending
                      || progress.available_xp < reward.cost_xp
                    }
                    onClick={() => redeemMutation.mutate(reward.id)}
                    variant="secondary"
                  >
                    {progress.available_xp < reward.cost_xp
                      ? "XP insuficiente"
                      : "Canjear recompensa"}
                  </Button>
                  <RewardDialog
                    reward={reward}
                    pending={rewardMutation.isPending}
                    onSave={(input) =>
                      rewardMutation.mutateAsync({ id: reward.id, input })
                    }
                  >
                    <button
                      className="icon-button"
                      aria-label={`Editar ${reward.name}`}
                    >
                      <Pencil aria-hidden="true" size={17} />
                    </button>
                  </RewardDialog>
                  <ConfirmDialog
                    title="¿Archivar recompensa?"
                    description="Dejará de aparecer entre las recompensas activas."
                    onConfirm={() => archiveRewardMutation.mutate(reward.id)}
                  >
                    <button
                      className="icon-button"
                      aria-label={`Archivar ${reward.name}`}
                    >
                      <Archive aria-hidden="true" size={17} />
                    </button>
                  </ConfirmDialog>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="planner-section finance-review">
        <div>
          <span className="eyebrow">Revisión financiera</span>
          <h2>Cierra tu revisión semanal</h2>
          <p>Confirma que revisaste el resumen. No se guardan montos, categorías ni conteos.</p>
        </div>
        <Button disabled={reviewMutation.isPending} onClick={() => reviewMutation.mutate()} variant="secondary">
          {reviewMutation.isPending ? "Guardando…" : "Marcar revisión completa"}
        </Button>
      </section>

      {(challengeMutation.isError || rewardMutation.isError || redeemMutation.isError || reviewMutation.isError) && (
        <p className="inline-error" role="alert">
          No se pudo completar la acción. Los datos anteriores se conservaron.
        </p>
      )}
    </ProgressFrame>
  );
}

function ProgressFrame({ children }: { children: ReactNode }) {
  return <div className="page page--wide">{children}</div>;
}

function ChallengeForm({
  habits,
  onSave,
  pending,
}: {
  habits: Habit[];
  onSave: (habitId: number | null, targetCount: number) => void;
  pending: boolean;
}) {
  const [habitId, setHabitId] = useState("");
  const [targetCount, setTargetCount] = useState(3);
  return (
    <form
      className="challenge-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(habitId ? Number(habitId) : null, targetCount);
      }}
    >
      <p>Elige una meta de uno a siete avances. Terminar la semana sin completarla no tiene penalización.</p>
      <div className="field"><label htmlFor="challenge-habit">Hábito</label><select id="challenge-habit" value={habitId} onChange={(event) => setHabitId(event.target.value)}><option value="">Todos los hábitos</option>{habits.map((habit) => <option value={habit.id} key={habit.id}>{habit.name}</option>)}</select></div>
      <div className="field"><label htmlFor="challenge-target">Meta semanal</label><input id="challenge-target" type="number" min={1} max={7} value={targetCount} onChange={(event) => setTargetCount(Number(event.target.value))} /></div>
      <Button disabled={pending} type="submit">{pending ? "Creando…" : "Crear desafío"}</Button>
    </form>
  );
}

function RewardDialog({
  children,
  onSave,
  pending,
  reward,
}: {
  children: ReactNode;
  onSave: (input: RewardInput) => Promise<unknown>;
  pending: boolean;
  reward?: Reward;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(reward?.name ?? "");
  const [description, setDescription] = useState(reward?.description ?? "");
  const [costXp, setCostXp] = useState(reward?.cost_xp ?? 50);
  async function submit(event: FormEvent) {
    event.preventDefault();
    await onSave({
      name: name.trim(),
      description: description.trim() || null,
      cost_xp: costXp,
    });
    setOpen(false);
  }
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{children}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-heading">
            <div><Dialog.Title>{reward ? "Editar recompensa" : "Crear recompensa"}</Dialog.Title><Dialog.Description>Una intención privada definida por ti.</Dialog.Description></div>
            <Dialog.Close className="icon-button" aria-label="Cerrar"><X aria-hidden="true" size={20} /></Dialog.Close>
          </div>
          <form className="dialog-form" onSubmit={submit}>
            <div className="field"><label htmlFor={`reward-name-${reward?.id ?? "new"}`}>Nombre</label><input id={`reward-name-${reward?.id ?? "new"}`} maxLength={80} required value={name} onChange={(event) => setName(event.target.value)} /></div>
            <div className="field"><label htmlFor={`reward-description-${reward?.id ?? "new"}`}>Descripción opcional</label><textarea id={`reward-description-${reward?.id ?? "new"}`} maxLength={240} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} /></div>
            <div className="field"><label htmlFor={`reward-cost-${reward?.id ?? "new"}`}>Costo en XP</label><input id={`reward-cost-${reward?.id ?? "new"}`} type="number" min={1} max={10000} required value={costXp} onChange={(event) => setCostXp(Number(event.target.value))} /></div>
            <div className="dialog-actions"><Button variant="secondary" onClick={() => setOpen(false)}>Cancelar</Button><Button disabled={pending} type="submit">{pending ? "Guardando…" : "Guardar recompensa"}</Button></div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
