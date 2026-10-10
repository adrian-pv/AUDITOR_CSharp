import { Gauge, ListChecks, ScrollText } from "lucide-react";

const NAV_ITEMS = [
  { id: "dashboard", label: "Panel General", icon: Gauge },
  { id: "analyzer", label: "Analizador", icon: ScrollText },
  { id: "rules", label: "Reglas y Políticas", icon: ListChecks },
];

export default function Sidebar({ active, onNavigate, auditor }) {
  return (
    <aside className="w-56 shrink-0 border-r border-stone-200 bg-white flex flex-col justify-between">
      <div>
        <div className="px-5 py-5">
          <p className="font-mono text-[13px] font-semibold text-stone-900">AUDITOR_C#</p>
          <p className="text-[11px] text-stone-500 mt-0.5">Gobierno &amp; auditoría continua</p>
        </div>
        <nav className="px-3 space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = active === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 text-[13px] rounded-md transition-colors ${
                  isActive
                    ? "bg-stone-900 text-white"
                    : "text-stone-600 hover:bg-stone-100"
                }`}
              >
                <Icon size={15} strokeWidth={1.75} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>
      <div className="px-5 py-4 border-t border-stone-200 text-[11px] text-stone-500 leading-relaxed">
        Auditor
        <br />
        <span className="text-stone-800">{auditor}</span>
      </div>
    </aside>
  );
}
