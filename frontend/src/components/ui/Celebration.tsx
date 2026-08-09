import { Award, Check, Gift, Sparkles, X } from "lucide-react";

type CelebrationKind = "check-in" | "milestone" | "reward";

interface CelebrationProps {
  description: string;
  kind?: CelebrationKind;
  onDismiss?: () => void;
  title: string;
}

const icons = {
  "check-in": Check,
  milestone: Award,
  reward: Gift,
};

export function Celebration({
  description,
  kind = "milestone",
  onDismiss,
  title,
}: CelebrationProps) {
  const Icon = icons[kind];

  return (
    <div className={`celebration celebration--${kind}`} role="status">
      <div aria-hidden="true" className="celebration__particles">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <span className="celebration__icon">
        <Icon aria-hidden="true" size={24} strokeWidth={1.8} />
      </span>
      <div className="celebration__copy">
        <span className="celebration__eyebrow">
          <Sparkles aria-hidden="true" size={14} />
          Momento reconocido
        </span>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
      {onDismiss && (
        <button
          aria-label="Cerrar celebración"
          className="celebration__close"
          onClick={onDismiss}
          type="button"
        >
          <X aria-hidden="true" size={18} />
        </button>
      )}
    </div>
  );
}
