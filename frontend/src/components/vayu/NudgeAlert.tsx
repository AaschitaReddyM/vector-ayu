import type { ReactNode } from "react";

export function NudgeAlert({
  icon,
  title,
  description,
  tone = "amber",
}: {
  icon: string;
  title: string;
  description: ReactNode;
  tone?: "amber" | "coral" | "blue" | "teal" | "purple";
}) {
  const TONE = {
    amber: { bg: "rgba(255,179,71,0.08)", border: "rgba(255,179,71,0.2)", color: "#ffb347" },
    coral: { bg: "rgba(255,107,107,0.08)", border: "rgba(255,107,107,0.2)", color: "#ff6b6b" },
    blue: { bg: "rgba(78,168,222,0.08)", border: "rgba(78,168,222,0.2)", color: "#4ea8de" },
    teal: { bg: "rgba(0,212,170,0.08)", border: "rgba(0,212,170,0.2)", color: "#00d4aa" },
    purple: { bg: "rgba(167,139,250,0.08)", border: "rgba(167,139,250,0.2)", color: "#a78bfa" },
  }[tone];
  return (
    <div
      className="rounded-[12px] p-4 border flex items-start gap-3 hover-lift animate-fade-up"
      style={{ background: TONE.bg, borderColor: TONE.border }}
    >
      <div
        className="w-10 h-10 rounded-[10px] flex items-center justify-center text-lg flex-shrink-0"
        style={{ background: `${TONE.color}22`, color: TONE.color }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-[0.85rem] font-semibold" style={{ color: TONE.color }}>
          {title}
        </div>
        <div className="text-[0.78rem] text-text-dim mt-1 leading-relaxed">{description}</div>
      </div>
    </div>
  );
}
