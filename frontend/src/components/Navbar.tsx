import { Activity, Database, FilePlus2, History, LayoutDashboard } from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/submit", label: "Submit Job", icon: FilePlus2 },
  { to: "/backends", label: "Backends", icon: Database },
  { to: "/jobs", label: "Jobs", icon: History },
  { to: "/results", label: "Results", icon: Activity }
];

export default function Navbar() {
  return (
    <nav className="border-b border-line bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <div>
          <p className="text-sm font-semibold text-ink">Quantum Orchestrator</p>
          <p className="text-xs text-slate-500">Hardware-agnostic cloud execution</p>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-quantum text-white" : "text-slate-700 hover:bg-slate-100"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
