import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQueries, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Activity, AlertTriangle, Users, Zap } from "lucide-react";
import { HexMapPlaceholder } from "@/components/vayu/HexMap";
import { PatientCard } from "@/components/vayu/PatientCard";
import { StatCard } from "@/components/vayu/StatCard";
import { patientsQuery, riskScoresQuery, triageQuery } from "@/lib/queries";
import { PATIENT_CONDITION } from "@/lib/mock-data";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [{ title: "Vector-AYU — 72-Hour Provider Triage" }],
  }),
  loader: ({ context }) => {
    context.queryClient.ensureQueryData(patientsQuery);
    context.queryClient.ensureQueryData(riskScoresQuery);
    context.queryClient.ensureQueryData(triageQuery);
  },
  component: DashboardPage,
  errorComponent: ({ error }) => (
    <div className="p-10 text-coral">Failed to load: {error.message}</div>
  ),
  notFoundComponent: () => <div className="p-10">Not found</div>,
});

function DashboardPage() {
  const queryClient = useQueryClient();
  const [{ data: patients }, { data: scores }, { data: triage }] = useSuspenseQueries({
    queries: [patientsQuery, riskScoresQuery, triageQuery],
  });

  const patientMap = new Map(patients.map((p) => [p.id, p]));
  const scoreMap = new Map(scores.map((s) => [s.patient_id, s]));
  const top = [...triage].sort((a, b) => b.risk_total - a.risk_total);
  const critical = top.filter((t) => t.risk_total >= 85).length;
  const high = top.filter((t) => t.risk_total >= 70 && t.risk_total < 85).length;

  return (
    <div className="max-w-[1440px] mx-auto px-7 py-7 flex flex-col gap-6">
      <div className="animate-fade-up flex justify-between items-start">
        <div>
          <h1 className="text-[1.7rem] font-extrabold tracking-tight">
            <span className="mr-2">🫁</span> 72-Hour Triage Dashboard
          </h1>
          <p className="text-[0.88rem] text-text-dim mt-1.5">
            High-risk patients ranked by climate volatility delta · DFW Metro
          </p>
        </div>
        <button
          className="bg-teal text-background px-4 py-2 rounded font-semibold hover:bg-teal-dim transition"
          onClick={async (e) => {
            e.preventDefault();
            try {
              const ptToSimulate = top.length > 0 ? top[0].patient_id : "PT-0001";
              toast.loading("Running ML Pipeline...", { id: "sim" });
              const apiUrl = import.meta.env.VITE_API_URL || "";
              const res = await fetch(`${apiUrl}/api/pipeline/run/${ptToSimulate}`, {
                method: "POST",
              });
              if (res.ok) {
                await queryClient.invalidateQueries({ queryKey: ["risk_scores"] });
                await queryClient.invalidateQueries({ queryKey: ["triage_queue"] });
                toast.success(`Pipeline executed for ${ptToSimulate}`, { id: "sim" });
              } else {
                toast.error(`Simulation failed: ${res.statusText}`, { id: "sim" });
              }
            } catch (err) {
              console.error("Simulation failed", err);
              toast.error("Network error during simulation", { id: "sim" });
            }
          }}
        >
          Run Live Simulation
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          label="Critical Risk"
          value={critical}
          sub="Risk score ≥ 85"
          accent="coral"
          icon={<AlertTriangle className="w-5 h-5" />}
        />
        <StatCard
          label="High Risk"
          value={high}
          sub="Risk score 70-84"
          accent="amber"
          icon={<Activity className="w-5 h-5" />}
        />
        <StatCard
          label="Active Cohort"
          value={patients.length}
          sub="Track A & B combined"
          accent="blue"
          icon={<Users className="w-5 h-5" />}
        />
        <StatCard
          label="Climate Δ Today"
          value="+2.41"
          sub="Top patient · respiratory head"
          accent="teal"
          icon={<Zap className="w-5 h-5" />}
        />
      </div>

      {/* Hex map */}
      <section className="bg-card border border-border rounded-[14px] overflow-hidden hover-lift animate-fade-up">
        <header className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-[0.95rem] font-semibold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-teal animate-pulse-dot" />
            🗺️ DFW Geospatial Risk Map — H3 Resolution 7
          </h2>
          <span className="text-[0.72rem] text-text-muted">Live · Updated 2 min ago</span>
        </header>
        <div className="p-5">
          <HexMapPlaceholder />
        </div>
      </section>

      {/* Patient queue */}
      <section className="animate-fade-up">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[1.05rem] font-bold">📋 Patient Triage Queue</h2>
          <span className="text-[0.72rem] text-text-dim">Sorted by Climate Volatility Δ ↓</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {top.map((t) => {
            const p = patientMap.get(t.patient_id);
            const s = scoreMap.get(t.patient_id);
            if (!p || !s) return null;
            return <PatientCard key={t.id} patient={p} score={s} riskTotal={t.risk_total} />;
          })}
        </div>
      </section>

      {/* Triage table */}
      <section className="bg-card border border-border rounded-[14px] overflow-hidden animate-fade-up">
        <header className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-[0.95rem] font-semibold">Full Queue · Detailed</h2>
        </header>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[0.7rem] uppercase tracking-wider text-text-dim border-b border-border">
                <th className="text-left px-5 py-3 font-medium">Patient ID</th>
                <th className="text-left px-5 py-3 font-medium">Name</th>
                <th className="text-left px-5 py-3 font-medium">Condition</th>
                <th className="text-left px-5 py-3 font-medium">Risk</th>
                <th className="text-left px-5 py-3 font-medium">Status</th>
                <th className="text-right px-5 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {top.map((t) => {
                const p = patientMap.get(t.patient_id);
                if (!p) return null;
                const color =
                  t.risk_total >= 85 ? "#ff6b6b" : t.risk_total >= 70 ? "#ffb347" : "#4ea8de";
                return (
                  <tr
                    key={t.id}
                    className="border-b border-border last:border-0 hover:bg-white/[0.02] transition"
                  >
                    <td className="px-5 py-3 font-bold text-teal">{p.id}</td>
                    <td className="px-5 py-3">
                      {p.given_name} {p.family_name}
                    </td>
                    <td className="px-5 py-3 text-text-dim">{PATIENT_CONDITION[p.id]}</td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2 min-w-[120px]">
                        <div className="flex-1 h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
                          <div
                            className="h-full"
                            style={{ width: `${t.risk_total}%`, background: color }}
                          />
                        </div>
                        <span className="font-bold tabular-nums" style={{ color }}>
                          {t.risk_total}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`text-[0.7rem] font-semibold px-2 py-0.5 rounded ${
                          t.status === "accepted"
                            ? "bg-teal/10 text-teal"
                            : t.status === "deferred"
                              ? "bg-amber/10 text-amber"
                              : "bg-purple/10 text-purple"
                        }`}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Link
                        to="/patient/$id"
                        params={{ id: p.id }}
                        className="text-[0.78rem] font-semibold text-teal hover:underline"
                      >
                        Review →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
