import { Gauge, History, ListChecks, LogOut, ScrollText, UserRound, Users } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const NAV_ITEMS = [
  { id: "dashboard", label: "Panel General", icon: Gauge },
  { id: "analyzer", label: "Analizador", icon: ScrollText },
  { id: "history", label: "Historial", icon: History },
  { id: "rules", label: "Reglas y Políticas", icon: ListChecks },
  { id: "users", label: "Usuarios", icon: Users, soloAdmin: true },
];

function NavButton({ item, active, onNavigate }) {
  const Icon = item.icon;
  const isActive = active === item.id;
  return (
    <button
      onClick={() => onNavigate(item.id)}
      className={`btn-press group w-full flex items-center gap-2.5 px-3 py-2 text-[13px] rounded-md transition-colors duration-150 ${
        isActive ? "bg-stone-900 text-white" : "text-stone-600 hover:bg-stone-100"
      }`}
    >
      <Icon size={15} strokeWidth={1.75} className="transition-transform duration-150 group-hover:scale-110" />
      {item.label}
    </button>
  );
}

export default function Sidebar({ active, onNavigate }) {
  const { usuario, esAdmin, logout } = useAuth();
  const items = NAV_ITEMS.filter((i) => !i.soloAdmin || esAdmin);

  return (
    <aside className="w-56 shrink-0 border-r border-stone-200 bg-white flex flex-col justify-between">
      <div>
        <div className="px-5 py-5">
          <p className="font-mono text-[13px] font-semibold text-stone-900">AUDITOR_C#</p>
          <p className="text-[11px] text-stone-500 mt-0.5">Gobierno &amp; auditoría continua</p>
        </div>
        <nav className="px-3 space-y-0.5">
          {items.map((item) => (
            <NavButton key={item.id} item={item} active={active} onNavigate={onNavigate} />
          ))}
        </nav>
      </div>

      <div className="border-t border-stone-200 p-3 space-y-0.5">
        <div className="px-3 pt-1 pb-2">
          <p className="text-[12.5px] text-stone-900 truncate">{usuario.nombre}</p>
          <p className="text-[11px] text-stone-500">{usuario.rol}</p>
        </div>
        <NavButton
          item={{ id: "profile", label: "Mi perfil", icon: UserRound }}
          active={active}
          onNavigate={onNavigate}
        />
        <button
          onClick={() => logout()}
          className="w-full flex items-center gap-2.5 px-3 py-2 text-[13px] rounded-md text-stone-600 hover:bg-stone-100"
        >
          <LogOut size={15} strokeWidth={1.75} />
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
