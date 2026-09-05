import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQueries, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Activity, AlertTriangle, Users, Zap } from "lucide-react";
import { HexMapPlaceholder } from "@/components/vayu/HexMap";
import { PatientCard } from "@/components/vayu/PatientCard";
import { StatCard } from "@/components/vayu/StatCard";
import { useState } from "react";
import { patientsQuery, riskScoresQuery, triageQuery } from "@/lib/queries";
import { getPatientCondition } from "@/lib/mock-data";

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
  const top = [...triage].sort((a, b) => b.risk_total - a.risk_total).slice(0, 12);
  const critical = top.filter((t) => t.risk_total >= 85).length;
  const high = top.filter((t) => t.risk_total >= 70 && t.risk_total < 85).length;

  const [selectedPatientId, setSelectedPatientId] = useState<string>("PT-0006"); // Start with Lin for the pitch
  const [cronResult, setCronResult] = useState<any>(null);
  const [showSandbox, setShowSandbox] = useState(false);
  const [overrides, setOverrides] = useState({ spo2: "", systolic_bp: "", custom_aqi: "" });
  const [anomalyType, setAnomalyType] = useState<string>("respiratory");

  return (
    <div className="max-w-[1440px] mx-auto px-7 py-7 flex flex-col gap-6">
      <div className="animate-fade-up flex justify-between items-start">
        <div>
          <h1 className="text-[1.7rem] font-extrabold tracking-tight">
            <span className="mr-2">🫁</span> 72-Hour Triage Dashboard
          </h1>
          <p className="text-[0.88rem] text-text-dim mt-1.5">
            High-risk patients ranked by climate volatility delta · {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi' ? 'NCR (National Capital Region)' : 'DFW Metro'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className={`px-4 py-2 rounded-lg font-semibold transition flex items-center gap-2 cursor-pointer ${
              showSandbox
                ? 'bg-amber text-background shadow-[0_0_15px_rgba(245,158,11,0.25)]'
                : 'bg-card border border-border text-amber hover:bg-amber/10'
            }`}
            onClick={() => setShowSandbox(!showSandbox)}
          >
            🧪 Clinical Sandbox {showSandbox ? '▲' : '▼'}
          </button>
          
          <div className="flex border border-coral/50 rounded-lg overflow-hidden shrink-0 shadow-[0_0_20px_rgba(255,107,107,0.15)] bg-coral/5">
            <select
              value={anomalyType}
              onChange={(e) => setAnomalyType(e.target.value)}
              className="bg-transparent text-coral px-3.5 py-2 text-sm font-medium focus:outline-none cursor-pointer border-r border-coral/40"
            >
              {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi' ? (
                <>
                  <option value="respiratory" className="bg-[#12141f] text-foreground">Respiratory 🫁 (Crop Stubble Smog)</option>
                  <option value="cardiovascular" className="bg-[#12141f] text-foreground">Cardiovascular ❤️ (Pre-Monsoon Heatwave)</option>
                  <option value="metabolic" className="bg-[#12141f] text-foreground">Metabolic ⚡ (Monsoon Flash Flooding)</option>
                </>
              ) : (
                <>
                  <option value="respiratory" className="bg-[#12141f] text-foreground">Respiratory 🫁 (Wildfire Smoke Plume)</option>
                  <option value="cardiovascular" className="bg-[#12141f] text-foreground">Cardiovascular ❤️ (Extreme Heat Dome)</option>
                  <option value="metabolic" className="bg-[#12141f] text-foreground">Metabolic ⚡ (ERCOT Power Grid Failure)</option>
                </>
              )}
            </select>
            <button
              className="bg-coral text-background px-4 py-2 font-bold hover:bg-coral-dim transition flex items-center gap-1.5 whitespace-nowrap shrink-0 cursor-pointer"
              onClick={async (e) => {
                e.preventDefault();
                try {
                  toast.loading(`Simulating ${anomalyType} anomaly (DANGER)...`, { id: "cron" });
                  const apiUrl = import.meta.env.VITE_API_URL || "https://vector-ayu-213260234201.us-central1.run.app";
                  const res = await fetch(`${apiUrl}/api/cron/scan-climate?anomaly_type=${anomalyType}`, {
                    method: "POST",
                  });
                  if (res.ok) {
                    const data = await res.json();
                    await queryClient.invalidateQueries({ queryKey: ["risk_scores"] });
                    await queryClient.invalidateQueries({ queryKey: ["triage_queue"] });
                    toast.success(data.message, { id: "cron", duration: 5000 });
                    setCronResult(data);
                  } else {
                    toast.error(`Simulation failed: ${res.statusText}`, { id: "cron" });
                  }
                } catch (err) {
                  console.error("Cron failed", err);
                  toast.error("Network error during climate trigger", { id: "cron" });
                }
              }}
            >
              ⚡ Trigger Climate Alert
            </button>
          </div>
        </div>
      </div>

      {/* Clinical Sandbox Drawer (Inline) */}
      {showSandbox && (
        <div className="bg-amber/5 border border-amber/30 rounded-xl p-5 animate-fade-up">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <div>
              <h3 className="font-bold text-amber flex items-center gap-2">
                🧪 What-If Clinical Simulator
              </h3>
              <p className="text-xs text-text-dim mt-0.5">Select a patient, customize their biomarkers, and run inference to observe TFT risk score shifts.</p>
            </div>
            
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold uppercase text-text-dim">Patient:</span>
              <select 
                value={selectedPatientId}
                onChange={(e) => setSelectedPatientId(e.target.value)}
                className="bg-surface border border-border text-text px-3 py-1.5 rounded-lg text-sm focus:outline-none focus:border-amber"
              >
                {patients.map(p => (
                  <option key={p.id} value={p.id}>{p.id} — {p.given_name} {p.family_name}</option>
                ))}
              </select>
              
              <button
                className="bg-amber text-background px-4 py-1.5 rounded-lg font-bold text-sm hover:bg-amber-dim transition cursor-pointer"
                onClick={async (e) => {
                  e.preventDefault();
                  try {
                    toast.loading("Running Multi-Task TFT Pipeline...", { id: "sim" });
                    const apiUrl = import.meta.env.VITE_API_URL || "https://vector-ayu-213260234201.us-central1.run.app";
                    
                    const payload: any = {};
                    if (overrides.spo2) payload.spo2 = parseFloat(overrides.spo2);
                    if (overrides.systolic_bp) payload.systolic_bp = parseFloat(overrides.systolic_bp);
                    if (overrides.custom_aqi) payload.custom_aqi = parseInt(overrides.custom_aqi);
                    
                    const res = await fetch(`${apiUrl}/api/pipeline/run/${selectedPatientId}`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ overrides: payload })
                    });
                    if (res.ok) {
                      const data = await res.json();
                      
                      queryClient.setQueryData(["risk_scores"], (old: any) => {
                         if (!old) return old;
                         return old.map((s: any) => s.patient_id === selectedPatientId ? {
                            ...s,
                            combined_delta: data.risk.combined_delta,
                            probabilities: data.risk.probabilities,
                            top_head: data.risk.top_head
                         } : s);
                      });
                      
                      await queryClient.invalidateQueries({ queryKey: ["triage_queue"] });
                      toast.success(`Pipeline updated for ${selectedPatientId}!`, { id: "sim" });
                    } else {
                      toast.error(`Simulation failed: ${res.statusText}`, { id: "sim" });
                    }
                  } catch (err) {
                    console.error("Simulation failed", err);
                    toast.error("Network error during simulation", { id: "sim" });
                  }
                }}
              >
                ▶ Run Simulation
              </button>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2 border-t border-amber/15">
            <div>
              <label className="text-xs font-bold uppercase text-text-dim mb-2 block">Override SpO2 (%)</label>
              <input type="number" placeholder="e.g. 88 (Hypoxia)" className="w-full bg-black/40 border border-border rounded px-4 py-2 text-sm focus:border-amber focus:outline-none transition-colors" 
                value={overrides.spo2} onChange={e => setOverrides({...overrides, spo2: e.target.value})} />
            </div>
            <div>
              <label className="text-xs font-bold uppercase text-text-dim mb-2 block">Override Systolic BP (mmHg)</label>
              <input type="number" placeholder="e.g. 165 (Hypertension)" className="w-full bg-black/40 border border-border rounded px-4 py-2 text-sm focus:border-amber focus:outline-none transition-colors" 
                value={overrides.systolic_bp} onChange={e => setOverrides({...overrides, systolic_bp: e.target.value})} />
            </div>
            <div>
              <label className="text-xs font-bold uppercase text-text-dim mb-2 block">Force Local AQI</label>
              <input type="number" placeholder="e.g. 210 (Very Unhealthy)" className="w-full bg-black/40 border border-border rounded px-4 py-2 text-sm focus:border-amber focus:outline-none transition-colors" 
                value={overrides.custom_aqi} onChange={e => setOverrides({...overrides, custom_aqi: e.target.value})} />
            </div>
          </div>
        </div>
      )}


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

      {/* Cron Result Display */}
      {cronResult && cronResult.status === "Intervention Triggered" && (
        <section className="bg-red-950/20 border border-coral/50 rounded-[14px] overflow-hidden animate-fade-up p-5">
          <header className="mb-4">
            <h2 className="text-[1.1rem] font-bold text-coral flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Autonomous Intervention Triggered
            </h2>
            <p className="text-sm text-text-dim mt-1">{cronResult.message}</p>
          </header>
          
          <div className="flex flex-col gap-4">
            {cronResult.processed_patients?.map((ptData: any, i: number) => (
              <div key={i} className="bg-black/20 p-4 rounded-lg border border-white/5">
                <h3 className="font-semibold text-teal mb-2">
                  {ptData.patient?.id} — {ptData.patient?.given_name} {ptData.patient?.family_name}
                </h3>
                
                {/* SMS Display */}
                {ptData.drafted_sms && (
                  <div className="mb-3">
                    <span className="text-xs font-bold uppercase text-text-muted mb-1 block">Drafted SMS (Vertex AI)</span>
                    <div className="bg-white/5 p-3 rounded text-sm text-text italic">
                      "{ptData.drafted_sms}"
                    </div>
                  </div>
                )}
                
                {/* IoT Display */}
                {ptData.iot_shielding && (
                  <div className="mt-4">
                    <p className="text-[0.65rem] font-bold text-text-dim uppercase tracking-wider mb-2">
                      SMART HOME PAYLOAD ({ptData.iot_shielding?.device.toUpperCase()})
                    </p>
                    <pre className="bg-[#0a0a0e] text-amber text-[0.8rem] p-3 rounded overflow-x-auto border border-white/5">
                      {JSON.stringify(ptData.iot_shielding, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Hex map */}
      <section className="bg-card border border-border rounded-[14px] overflow-hidden hover-lift animate-fade-up">
        <header className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-[0.95rem] font-semibold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-teal animate-pulse-dot" />
            🗺️ {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi' ? 'National Capital Region Delhi' : 'Dallas Fort Worth'} Geospatial Risk Map — H3 Resolution 7
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
                <th className="text-left px-5 py-3 font-medium">Cohort</th>
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
                    <td className="px-5 py-3">
                      <span className={`text-[0.7rem] font-semibold px-2 py-0.5 rounded capitalize ${
                        t.head === 'respiratory' ? 'bg-amber/10 text-amber' : 
                        t.head === 'cardiovascular' ? 'bg-coral/10 text-coral' : 
                        'bg-purple/10 text-purple'
                      }`}>
                        {t.head} {t.head === 'respiratory' ? '🫁' : t.head === 'cardiovascular' ? '❤️' : '⚡'}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-text-dim">{getPatientCondition(p.id)}</td>
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
