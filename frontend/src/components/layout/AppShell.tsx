import {
  CalendarCheck,
  CircleDollarSign,
  Gauge,
  ListChecks,
  LogOut,
  Sprout,
  Users,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useSession } from "../../context/session-store";
import { OrganicMotif } from "../ui/OrganicMotif";

const navigation = [
  { label: "Hoy", path: "/", icon: CalendarCheck },
  { label: "Hábitos", path: "/habitos", icon: ListChecks },
  { label: "Finanzas", path: "/finanzas", icon: CircleDollarSign },
  { label: "Progreso", path: "/progreso", icon: Gauge },
];

export function AppShell() {
  const { logout, user } = useSession();
  const visibleNavigation = user?.role === "admin"
    ? [...navigation, { label: "Administración", path: "/administracion", icon: Users }]
    : navigation;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink aria-label="Inicio" className="brand" to="/">
          <span className="brand__mark">
            <Sprout aria-hidden="true" size={24} strokeWidth={1.7} />
          </span>
          <span>
            <strong>Pleno</strong>
            <small>Agenda personal</small>
          </span>
        </NavLink>

        <nav aria-label="Navegación principal" className="sidebar__nav">
          {visibleNavigation.map(({ icon: Icon, label, path }) => (
            <NavLink
              className={({ isActive }) =>
                `nav-link${isActive ? " nav-link--active" : ""}`
              }
              end={path === "/"}
              key={path}
              to={path}
            >
              <Icon aria-hidden="true" size={22} strokeWidth={1.7} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__session">
          <span>{user?.display_name}</span>
          <small>@{user?.username}</small>
          <button
            className="sidebar__logout"
            onClick={() => void logout()}
            type="button"
          >
            <LogOut aria-hidden="true" size={18} />
            Cerrar sesión
          </button>
        </div>
        <OrganicMotif className="sidebar__motif" variant="bloom" />
      </aside>

      <header className="mobile-header">
        <NavLink aria-label="Inicio" className="mobile-brand" to="/">
          <span className="brand__mark">
            <Sprout aria-hidden="true" size={22} strokeWidth={1.7} />
          </span>
          <span>
            <strong>Pleno</strong>
            <small>Agenda personal</small>
          </span>
        </NavLink>
        <button
          aria-label={`Cerrar sesión de ${user?.display_name}`}
          className="mobile-header__logout"
          onClick={() => void logout()}
          type="button"
        >
          <LogOut aria-hidden="true" size={21} />
        </button>
      </header>

      <main className="main-content">
        <Outlet />
      </main>

      <nav aria-label="Navegación móvil" className="mobile-nav">
        {visibleNavigation.map(({ icon: Icon, label, path }) => (
          <NavLink
            className={({ isActive }) =>
              `mobile-nav__link${isActive ? " mobile-nav__link--active" : ""}`
            }
            end={path === "/"}
            key={path}
            to={path}
          >
            <Icon aria-hidden="true" size={22} strokeWidth={1.8} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
