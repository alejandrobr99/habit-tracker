import { Flame, Sparkles, Trophy, X } from "lucide-react";
import { useEffect } from "react";

import type { SpectacleMoment } from "../../lib/celebrations";
import { OrganicMotif } from "./OrganicMotif";

interface StreakSpectacleProps {
  moment: SpectacleMoment;
  onDismiss: () => void;
}

const icons = {
  day: Sparkles,
  streak: Flame,
  target: Trophy,
};

const particles = Array.from({ length: 18 }, (_, index) => index);

export function StreakSpectacle({
  moment,
  onDismiss,
}: StreakSpectacleProps) {
  const Icon = icons[moment.kind];

  useEffect(() => {
    const timeout = window.setTimeout(onDismiss, 3_400);
    return () => window.clearTimeout(timeout);
  }, [onDismiss]);

  return (
    <div
      aria-live="polite"
      className={`spectacle spectacle--${moment.kind}`}
      role="status"
    >
      <div aria-hidden="true" className="spectacle__veil" />
      <div aria-hidden="true" className="spectacle__rays" />
      <div aria-hidden="true" className="spectacle__orbit spectacle__orbit--outer" />
      <div aria-hidden="true" className="spectacle__orbit spectacle__orbit--inner" />
      <OrganicMotif
        className="spectacle__motif spectacle__motif--left"
        variant="bloom"
      />
      <OrganicMotif
        className="spectacle__motif spectacle__motif--right"
        variant="sprout"
      />
      <div aria-hidden="true" className="spectacle__particles">
        {particles.map((particle) => (
          <span key={particle} />
        ))}
      </div>
      <div className="spectacle__content">
        <span className="spectacle__kicker">
          <Sparkles aria-hidden="true" size={17} />
          {moment.eyebrow}
          <Sparkles aria-hidden="true" size={17} />
        </span>
        <span className="spectacle__emblem">
          <Icon aria-hidden="true" size={44} strokeWidth={1.6} />
        </span>
        <strong className="spectacle__value">{moment.value}</strong>
        <span className="spectacle__unit">{moment.unit}</span>
        <h2>{moment.title}</h2>
        <p>{moment.description}</p>
      </div>
      <button
        aria-label="Cerrar celebración"
        className="spectacle__close"
        onClick={onDismiss}
        type="button"
      >
        <X aria-hidden="true" size={22} />
      </button>
    </div>
  );
}
