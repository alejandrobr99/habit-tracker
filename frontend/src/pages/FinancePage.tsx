import { ArrowDownRight, ArrowUpRight, Landmark, LockKeyhole } from "lucide-react";

export function FinancePage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Dinero con intención</span>
          <h1>Finanzas</h1>
          <p>Un presupuesto simple para tomar decisiones con tranquilidad.</p>
        </div>
        <span className="coming-badge">Próximamente</span>
      </header>

      <section aria-label="Vista previa del presupuesto" className="finance-preview">
        <div className="finance-total">
          <span>Disponible este mes</span>
          <strong>—</strong>
          <p>Agosto · Presupuesto por configurar</p>
        </div>
        <div className="finance-stat">
          <span className="summary-card__icon summary-card__icon--sage">
            <ArrowDownRight aria-hidden="true" size={19} />
          </span>
          <div>
            <span>Ingresos</span>
            <strong>—</strong>
          </div>
        </div>
        <div className="finance-stat">
          <span className="summary-card__icon summary-card__icon--clay">
            <ArrowUpRight aria-hidden="true" size={19} />
          </span>
          <div>
            <span>Gastos</span>
            <strong>—</strong>
          </div>
        </div>
      </section>

      <section className="coming-panel">
        <span className="coming-panel__icon">
          <Landmark aria-hidden="true" size={25} />
        </span>
        <div>
          <span className="eyebrow">En preparación</span>
          <h2>Tu presupuesto, sin complicaciones</h2>
          <p>
            Estamos diseñando categorías, movimientos y metas mensuales para
            que puedas entender tu dinero de un vistazo.
          </p>
          <ul>
            <li>Presupuesto mensual por categorías</li>
            <li>Registro ágil de ingresos y gastos</li>
            <li>Metas de ahorro y balance del mes</li>
          </ul>
          <span className="privacy-note">
            <LockKeyhole aria-hidden="true" size={15} />
            Tus datos financieros serán privados y estarán bajo tu control.
          </span>
        </div>
      </section>
    </div>
  );
}
