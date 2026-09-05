import { Link } from "@tanstack/react-router";
import type { Patient, RiskScore } from "@/lib/mock-data";
import { getPatientCondition } from "@/lib/mock-data";

function riskColor(risk: number) {
  if (risk >= 85) return "#ff6b6b";
  if (risk >= 70) return "#ffb347";
  return "#4ea8de";
}
function tierLabel(risk: number) {
  if (risk >= 85) return "Critical";
  if (risk >= 70) return "High";
  return "Moderate";
}

export function PatientCard({
  patient,
  score,
  riskTotal,
}: {
  patient: Patient;
  score: RiskScore;
  riskTotal: number;
}) {
  const color = riskColor(riskTotal);
  const tier = tierLabel(riskTotal);

  return (
    <Link
      to="/patient/$id"
      params={{ id: patient.id }}
      className="block bg-card border border-border rounded-[14px] p-5 hover-lift animate-fade-up"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <div className="text-teal font-bold text-[0.95rem]">{patient.id}</div>
          <div className="text-[0.92rem] font-semibold mt-0.5 truncate">
            {patient.given_name} {patient.family_name}
          </div>
          <div className="text-[0.72rem] text-text-dim mt-1.5 flex items-center gap-2">
            <span>ZIP {patient.postal_code}</span>
            <span className="bg-white/5 text-white/70 px-1.5 py-0.5 rounded text-[0.65rem] uppercase font-bold tracking-wider">
              {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi'
                ? (patient.primary_language === "es" ? "Telugu" : "Hindi")
                : (patient.primary_language === "es" ? "Español" : "English")}
            </span>
            <span className={`px-1.5 py-0.5 rounded text-[0.65rem] uppercase font-bold tracking-wider ${
              score.top_head === 'respiratory' ? 'bg-amber/10 text-amber' : 
              score.top_head === 'cardiovascular' ? 'bg-coral/10 text-coral' : 
              'bg-purple/10 text-purple'
            }`}>
              {score.top_head} {score.top_head === 'respiratory' ? '🫁' : score.top_head === 'cardiovascular' ? '❤️' : '⚡'}
            </span>
          </div>
        </div>
        <span
          className="text-[0.68rem] font-bold px-2.5 py-1 rounded-md uppercase tracking-wider"
          style={{ background: `${color}22`, color }}
        >
          {tier}
        </span>
      </div>
      <div className="text-[0.72rem] text-text-dim mb-2">
        {getPatientCondition(patient.id) ?? "COPD"}
      </div>
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${riskTotal}%`, background: color }}
          />
        </div>
        <span className="text-[0.85rem] font-bold tabular-nums" style={{ color }}>
          {riskTotal}
        </span>
      </div>
      <div className="mt-3 text-[0.68rem] text-text-muted">
        Climate Δ{" "}
        <span className="text-coral font-semibold">+{score.combined_delta.toFixed(2)}</span>
      </div>
    </Link>
  );
}
