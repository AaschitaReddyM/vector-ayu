import type { ReactNode } from "react";

type Props = {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: "teal" | "coral" | "amber" | "blue" | "purple";
  icon?: ReactNode;
};

const ACCENTS = {
  teal: { color: "#00d4aa", bg: "rgba(0,212,170,0.1)" },
  coral: { color: "#ff6b6b", bg: "rgba(255,107,107,0.1)" },
  amber: { color: "#ffb347", bg: "rgba(255,179,71,0.1)" },
  blue: { color: "#4ea8de", bg: "rgba(78,168,222,0.1)" },
  purple: { color: "#a78bfa", bg: "rgba(167,139,250,0.1)" },
};

export function StatCard({ label, value, sub, accent = "teal", icon }: Props) {
  const a = ACCENTS[accent];
  return (
    <div className="bg-card border border-border rounded-[14px] p-5 hover-lift relative overflow-hidden animate-fade-up">
      <div
        className="absolute top-0 left-0 right-0 h-[3px]"
        style={{
          background: `linear-gradient(90deg, ${a.color}, transparent)`,
        }}
      />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[0.7rem] uppercase tracking-wider text-text-dim font-medium">
            {label}
          </div>
          <div
            className="text-[1.7rem] font-extrabold mt-1.5 tracking-tight"
            style={{ color: a.color }}
          >
            {value}
          </div>
          {sub && <div className="text-[0.72rem] text-text-dim mt-1.5">{sub}</div>}
        </div>
        {icon && (
          <div
            className="w-10 h-10 rounded-[10px] flex items-center justify-center flex-shrink-0"
            style={{ background: a.bg, color: a.color }}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
