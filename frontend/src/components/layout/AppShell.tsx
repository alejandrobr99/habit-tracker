import {
  CalendarCheck,
  CircleDollarSign,
  ListChecks,
  Sprout,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  { label: "Hoy", path: "/", icon: CalendarCheck },
  { label: "Hábitos", path: "/habitos", icon: ListChecks },
  { label: "Finanzas", path: "/finanzas", icon: CircleDollarSign },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink aria-label="Inicio" className="brand" to="/">
          <span className="brand__mark">
            <Sprout aria-hidden="true" size={20} strokeWidth={1.8} />
          </span>
          <span>
            <strong>Pleno</strong>
            <small>Agenda personal</small>
          </span>
        </NavLink>

        <nav aria-label="Navegación principal" className="sidebar__nav">
          {navigation.map(({ icon: Icon, label, path }) => (
            <NavLink
              className={({ isActive }) =>
                `nav-link${isActive ? " nav-link--active" : ""}`
              }
              end={path === "/"}
              key={path}
              to={path}
            >
              <Icon aria-hidden="true" size={19} strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>

        <p className="sidebar__note">
          Un lugar sereno para cuidar lo que importa.
        </p>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>

      <nav aria-label="Navegación móvil" className="mobile-nav">
        {navigation.map(({ icon: Icon, label, path }) => (
          <NavLink
            className={({ isActive }) =>
              `mobile-nav__link${isActive ? " mobile-nav__link--active" : ""}`
            }
            end={path === "/"}
            key={path}
            to={path}
          >
            <Icon aria-hidden="true" size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
