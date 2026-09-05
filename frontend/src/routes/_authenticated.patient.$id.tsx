import { useState } from "react";
import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useSuspenseQueries, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { RiskRing } from "@/components/vayu/RiskRing";
import { RiskTrajectoryChart } from "@/components/vayu/RiskTrajectoryChart";
import { XaiBars } from "@/components/vayu/XaiBars";
import { patientQuery, riskScoreQuery } from "@/lib/queries";
import { MEDICATIONS, getPatientCondition, PATIENT_DRIVERS, RISK_TRAJECTORY } from "@/lib/mock-data";

export const Route = createFileRoute("/_authenticated/patient/$id")({
  head: ({ params }) => ({
    meta: [{ title: `Vector-AYU — Patient ${params.id}` }],
  }),
  loader: async ({ context, params }) => {
    await context.queryClient.ensureQueryData(patientQuery(params.id));
    await context.queryClient.ensureQueryData(riskScoreQuery(params.id));
  },
  component: PatientDetail,
  errorComponent: ({ error }) => <div className="p-10 text-coral">Failed: {error.message}</div>,
  notFoundComponent: () => (
    <div className="p-10 text-center">
      <h1 className="text-2xl font-bold">Patient not found</h1>
      <Link to="/dashboard" className="text-teal mt-4 inline-block">
        ← Back to dashboard
      </Link>
    </div>
  ),
});

const RING_COLORS = {
  respiratory: "#ff6b6b",
  cardiovascular: "#ffb347",
  metabolic: "#4ea8de",
};

function PatientDetail() {
  const queryClient = useQueryClient();
  const { id } = Route.useParams();
  const [{ data: patient }, { data: score }] = useSuspenseQueries({
    queries: [patientQuery(id), riskScoreQuery(id)],
  });
  if (!patient || !score) throw notFound();

  const age = new Date().getFullYear() - new Date(patient.birth_date).getFullYear();
  const defaultDrivers =
    PATIENT_DRIVERS[patient.id] ?? PATIENT_DRIVERS[Object.keys(PATIENT_DRIVERS)[0]];
  const [activeDrivers, setActiveDrivers] = useState(defaultDrivers);
  const condition = getPatientCondition(patient.id) ?? "COPD";

  return (
    <div className="max-w-[1440px] mx-auto px-7 py-7 flex flex-col gap-6">
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-2 text-[0.82rem] text-text-dim hover:text-teal transition w-fit"
      >
        <ArrowLeft className="w-4 h-4" /> Back to triage queue
      </Link>

      {/* Header */}
      <div className="bg-card border border-border rounded-[14px] p-7 grid md:grid-cols-3 gap-5 items-center relative overflow-hidden animate-fade-up">
        <div
          className="absolute bottom-0 left-0 right-0 h-[3px]"
          style={{
            background: "linear-gradient(90deg, #00d4aa, #4ea8de, #a78bfa, #00d4aa)",
            backgroundSize: "200% 100%",
            animation: "gradientSlide 4s linear infinite",
          }}
        />
        <div>
          <div className="text-[1.6rem] font-extrabold text-teal tracking-tight">{patient.id}</div>
          <div className="text-[1.05rem] font-semibold mt-1">
            {patient.given_name} {patient.family_name}
          </div>
          <div className="text-[0.82rem] text-text-dim mt-1">
            Age {age} · {patient.gender} · ZIP {patient.postal_code} ·{" "}
            {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi' 
              ? (patient.primary_language === "es" ? "Telugu" : "Hindi") 
              : (patient.primary_language === "es" ? "Español" : "English")}
          </div>
        </div>
        <div className="flex flex-col items-center gap-2">
          <code className="text-[0.78rem] font-mono bg-white/[0.04] px-3 py-1 rounded-md border border-border text-text-dim">
            H3: 872a1072bffffff <span className="text-text-muted">(Res 7)</span>
          </code>
          <div className="text-[0.78rem] text-text-dim flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-teal shadow-[0_0_8px_rgba(0,212,170,0.5)]" />
            Full Telemetry Active
          </div>
        </div>
        <div className="flex flex-col gap-2 items-end md:justify-end">
          <span className="text-[0.72rem] font-semibold px-3 py-1 rounded-md bg-teal-dim text-teal">
            ✓ Consent Track A
          </span>
          <button
            className="bg-teal text-background px-3 py-1.5 rounded-md text-sm font-bold hover:bg-teal-dim transition"
            onClick={async (e) => {
              e.preventDefault();
              try {
                toast.loading("Running Pipeline...", { id: "sim2" });
                const apiUrl = import.meta.env.VITE_API_URL || "https://vector-ayu-213260234201.us-central1.run.app";
                const res = await fetch(`${apiUrl}/api/pipeline/run/${patient.id}`, {
                  method: "POST",
                });
                if (res.ok) {
                  const data = await res.json();
                  if (data.top_drivers && data.top_drivers.length > 0) {
                    setActiveDrivers(data.top_drivers);
                  }
                  await queryClient.invalidateQueries({ queryKey: ["risk_score", patient.id] });
                  await queryClient.invalidateQueries({ queryKey: ["risk_scores"] });
                  await queryClient.invalidateQueries({ queryKey: ["triage_queue"] });
                  toast.success("Pipeline successful!", { id: "sim2" });
                } else {
                  toast.error(`Simulation failed: ${res.statusText}`, { id: "sim2" });
                }
              } catch (err) {
                console.error("Failed to run pipeline:", err);
                toast.error("Network error during simulation", { id: "sim2" });
              }
            }}
          >
            Simulate Pipeline
          </button>
        </div>
      </div>

      {/* Risk Rings */}
      <section className="bg-card border border-border rounded-[14px] p-7 animate-fade-up">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[1.05rem] font-bold">🎯 Risk Probabilities — Next 72h</h2>
          <span className="text-[0.72rem] text-text-dim">
            Top firing head:{" "}
            <span className="text-coral font-semibold uppercase">{score.top_head}</span>
          </span>
        </div>
        <div className="grid grid-cols-3 gap-6">
          {(["respiratory", "cardiovascular", "metabolic"] as const).map((head) => (
            <div key={head} className="flex flex-col items-center gap-3">
              <RiskRing
                value={score.probabilities[head]}
                color={RING_COLORS[head]}
                size={140}
                label={head}
              />
              <div className="text-[0.7rem] text-text-muted text-center">
                Climate Δ{" "}
                <span className="text-coral font-semibold">
                  +{score.climate_volatility_delta[head].toFixed(2)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Clinical */}
        <section className="bg-card border border-border rounded-[14px] overflow-hidden animate-fade-up">
          <header className="px-5 py-4 border-b border-border flex items-center justify-between">
            <h2 className="text-[0.95rem] font-semibold">🩺 Clinical Profile</h2>
            <span className="text-[0.7rem] font-semibold px-2 py-0.5 rounded bg-coral/10 text-coral">
              {condition}
            </span>
          </header>
          <div className="p-5">
            {[
              ["Primary Condition", condition],
              ["FEV1", "38% predicted", "coral"],
              ["Last Spirometry", "2026-04-15"],
              ["Comorbidities", "Hypertension, Osteoporosis"],
              ["Smoking Status", "Former — 35 pack-years", "amber"],
              ["Prior Exacerbations (12mo)", "4", "coral"],
              ["Prior ER Visits (12mo)", "2", "coral"],
            ].map((row, i) => (
              <div
                key={i}
                className="flex justify-between py-2.5 border-b border-border last:border-0 text-sm"
              >
                <span className="text-text-dim">{row[0]}</span>
                <span
                  className="font-semibold"
                  style={{
                    color:
                      row[2] === "coral" ? "#ff6b6b" : row[2] === "amber" ? "#ffb347" : "#f0f4f8",
                  }}
                >
                  {row[1]}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Medications */}
        <section className="bg-card border border-border rounded-[14px] overflow-hidden animate-fade-up">
          <header className="px-5 py-4 border-b border-border flex items-center justify-between">
            <h2 className="text-[0.95rem] font-semibold">💊 Medication List</h2>
            <span className="text-[0.72rem] text-text-muted">{MEDICATIONS.length} active</span>
          </header>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[0.68rem] uppercase tracking-wider text-text-dim border-b border-border">
                <th className="text-left px-4 py-2.5 font-medium">Medication</th>
                <th className="text-left px-4 py-2.5 font-medium">Type</th>
                <th className="text-left px-4 py-2.5 font-medium">Adherence</th>
              </tr>
            </thead>
            <tbody>
              {MEDICATIONS.map((m) => (
                <tr
                  key={m.name}
                  className="border-b border-border last:border-0 hover:bg-white/[0.02]"
                >
                  <td className="px-4 py-3 font-medium text-[0.82rem]">{m.name}</td>
                  <td className="px-4 py-3">
                    <span
                      className="text-[0.66rem] font-semibold px-2 py-0.5 rounded"
                      style={{
                        background: `var(--${m.typeColor})22`,
                        color: `var(--${m.typeColor})`,
                      }}
                    >
                      {m.type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {m.adherence !== null ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded bg-white/[0.05] overflow-hidden">
                          <div className="h-full bg-teal" style={{ width: `${m.adherence}%` }} />
                        </div>
                        <span className="text-teal font-semibold text-[0.78rem]">
                          {m.adherence}%
                        </span>
                      </div>
                    ) : (
                      <span className="text-text-dim text-[0.78rem]">PRN</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      {/* XAI */}
      <section className="bg-card border border-border rounded-[14px] overflow-hidden animate-fade-up">
        <header className="px-5 py-4 border-b border-border flex items-center justify-between">
          <h2 className="text-[0.95rem] font-semibold">🔍 XAI Feature Attribution</h2>
          <span className="text-[0.72rem] text-text-dim">Clinical priors × patient deviation</span>
        </header>
        <div className="p-5">
          <XaiBars drivers={activeDrivers} />
        </div>
      </section>

      {/* Trajectory */}
      <section className="bg-card border border-border rounded-[14px] overflow-hidden animate-fade-up">
        <header className="px-5 py-4 border-b border-border flex items-center justify-between">
          <h2 className="text-[0.95rem] font-semibold">📈 72-Hour Risk Trajectory</h2>
          <span className="text-[0.7rem] font-semibold px-2 py-0.5 rounded bg-coral/10 text-coral animate-pulse-dot">
            LIVE
          </span>
        </header>
        <div className="p-5">
          <RiskTrajectoryChart data={RISK_TRAJECTORY} />
        </div>
      </section>

      {/* Hyper-Local AI Care Plan & Logistics */}
      <div className="grid lg:grid-cols-2 gap-6 mb-10">
        <section className="bg-teal-950/20 border border-teal/20 rounded-[14px] overflow-hidden animate-fade-up">
          <header className="px-5 py-4 border-b border-teal/10 flex items-center justify-between">
            <h2 className="text-[0.95rem] font-semibold text-teal flex items-center gap-2">
              🤖 AI Generated Care Plan
            </h2>
            <span className="text-[0.65rem] font-bold px-2 py-0.5 rounded bg-teal/10 text-teal uppercase tracking-wider">
              {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi' ? 'AIIMS / Localized' : 'UTSW / Localized'}
            </span>
          </header>
          <div className="p-5 text-sm text-text-dim leading-relaxed space-y-4">
            {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi' ? (
              <>
                <p>
                  <strong>Immediate Threat:</strong> Severe AQI degradation due to regional stubble burning and low wind speeds in the NCR.
                </p>
                <p>
                  <strong>Action Plan:</strong><br/>
                  1. Keep patient indoors with air purifiers on max mode.<br/>
                  2. Ensure daily controller inhaler adherence.<br/>
                  3. If SpO2 drops below 92% or wheezing worsens, call <strong>112</strong> immediately or proceed to the nearest emergency ward at <strong>AIIMS New Delhi</strong>.
                </p>
              </>
            ) : (
              <>
                <p>
                  <strong>Immediate Threat:</strong> Incoming wildfire smoke plume driving PM2.5 to hazardous levels across the DFW Metroplex.
                </p>
                <p>
                  <strong>Action Plan:</strong><br/>
                  1. Keep windows closed and ensure home HVAC is running with MERV-13 filters.<br/>
                  2. Maintain strict adherence to daily controller therapies.<br/>
                  3. If respiratory distress occurs, dial <strong>911</strong> immediately or visit the <strong>UT Southwestern Medical Center</strong> ER.
                </p>
              </>
            )}
          </div>
        </section>

        <section className="bg-card border border-border rounded-[14px] overflow-hidden animate-fade-up">
          <header className="px-5 py-4 border-b border-border flex items-center justify-between">
            <h2 className="text-[0.95rem] font-semibold flex items-center gap-2">
              🚚 Automated Logistics & Dispatch
            </h2>
            <span className="text-[0.65rem] font-bold px-2 py-0.5 rounded bg-purple/10 text-purple uppercase tracking-wider">
              Prepared
            </span>
          </header>
          <div className="p-5 text-sm space-y-4">
            <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5">
              <div className="flex flex-col">
                <span className="font-semibold text-text">Prophylactic Inhaler Refill</span>
                <span className="text-[0.75rem] text-text-dim">
                  {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi' 
                    ? 'Apollo Pharmacy via Swiggy Genie' 
                    : 'CVS Pharmacy via UberHealth'}
                </span>
              </div>
              <div className="text-right">
                <span className="block font-bold text-teal">
                  {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi' 
                    ? '₹ 450.00' 
                    : '$ 15.00'}
                </span>
                <span className="text-[0.65rem] text-text-dim">Covered by Insurance</span>
              </div>
            </div>
            <button className="w-full py-2 bg-purple/20 hover:bg-purple/30 text-purple font-semibold rounded-lg transition text-[0.8rem] border border-purple/20">
              Authorize Dispatch
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
