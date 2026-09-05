import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Check, Info } from "lucide-react";
import { Stepper, StepperCard } from "@/components/vayu/Stepper";
import { insertOutreach, outreachQuery } from "@/lib/queries";

export const Route = createFileRoute("/_authenticated/outreach")({
  head: () => ({ meta: [{ title: "Vector-AYU — Outreach Approval" }] }),
  loader: ({ context }) => context.queryClient.ensureQueryData(outreachQuery),
  component: OutreachPage,
  errorComponent: ({ error }) => <div className="p-10 text-coral">{error.message}</div>,
  notFoundComponent: () => <div className="p-10">Not found</div>,
});

const STEPS = [
  { icon: "⚡", label: "Patient Flagged", time: "14:23" },
  { icon: "🤖", label: "AI Outreach Generated", time: "14:24" },
  { icon: "👨‍⚕️", label: "Provider Review", time: "NOW" },
  { icon: "📨", label: "Message Scheduled" },
  { icon: "📋", label: "Logged in EHR" },
];

const getCampaigns = () => {
  const isNewDelhi = typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi';
  
  if (isNewDelhi) {
    return [
      {
        id: "track_a",
        name: "Stubble Smog Advisory — Respiratory Panel",
        trigger: "AQI >150 + Stubble Burning",
        population: "847 patients (Track A)",
        track: "A",
        messages: {
          en: "Air quality in the NCR region is expected to worsen over the next 48 hours due to stubble smoke. If you have a respiratory condition, we recommend keeping air purifiers on max, limiting outdoor activity, keeping your rescue inhaler accessible, and contacting your care team if symptoms worsen. — Your Vector-AYU Care Team",
          es: "NCR ప్రాంతంలో గాలి నాణ్యత క్షీణించే అవకాశం ఉంది. మీకు శ్వాసకోశ సమస్యలు ఉంటే దయచేసి ఇంట్లోనే ఉండండి. — మీ Vector-AYU కేర్ టీమ్", // Telugu
        }
      },
      {
        id: "track_b",
        name: "Pre-Monsoon Heatwave — Cardiovascular Panel",
        trigger: "Heat >45°C + High Humidity",
        population: "612 patients (Track B)",
        track: "B",
        messages: {
          en: "Extreme heat is expected in New Delhi over the next 48 hours. If you have a heart condition or high blood pressure, extreme heat forces your heart to work harder. We strongly advise staying in cooled environments, drinking plenty of water, and monitoring for swelling or dizziness. — Your Vector-AYU Care Team",
          es: "नई दिल्ली में अत्यधिक गर्मी की उम्मीद है। यदि आपको हृदय रोग है, तो कृपया ठंडे वातावरण में रहें और बहुत सारा पानी पिएं। — आपकी Vector-AYU केयर टीम", // Hindi
        }
      },
      {
        id: "track_c",
        name: "Monsoon Flash Flooding — Metabolic Panel",
        trigger: "Heavy Rainfall + Power Outage",
        population: "438 patients (Track C)",
        track: "C",
        messages: {
          en: "Heavy monsoon rains and potential flooding are expected in New Delhi. If you manage diabetes, ensure you have backup power for your insulin fridge and stock up on necessary supplies. Keep emergency contacts handy. — Your Vector-AYU Care Team",
          es: "नई दिल्ली में भारी मानसूनी बारिश की उम्मीद है। यदि आप मधुमेह के रोगी हैं, तो कृपया अपने इंसुलिन के लिए बैकअप पावर सुनिश्चित करें। — आपकी Vector-AYU केयर टीम", // Hindi
        }
      }
    ];
  }

  return [
    {
      id: "track_a",
      name: "Heat Advisory — Respiratory Panel",
      trigger: "AQI >150 + Heat >100°F",
      population: "847 patients (Track A)",
      track: "A",
      messages: {
        en: "Air quality in the Dallas metro area is expected to worsen over the next 48 hours due to elevated ozone and particulate levels. If you have a respiratory condition, we recommend limiting outdoor activity (especially 2–6 PM), keeping rescue inhaler accessible, running AC indoors, and contacting your care team if symptoms worsen. — Your Vector-AYU Care Team",
        es: "Se espera que la calidad del aire en el área metropolitana de Dallas empeore durante las próximas 48 horas debido a niveles elevados de ozono y partículas. Si tiene una condición respiratoria: limite la actividad al aire libre, mantenga su inhalador accesible, use aire acondicionado, y comuníquese con su equipo si los síntomas empeoran. — Su equipo Vector-AYU",
      }
    },
    {
      id: "track_b",
      name: "Extreme Heat — Cardiovascular Panel",
      trigger: "Heat >100°F + High Humidity",
      population: "612 patients (Track B)",
      track: "B",
      messages: {
        en: "Extreme heat is expected in Dallas over the next 48 hours. If you have a heart condition or high blood pressure, extreme heat forces your heart to work harder. We strongly advise staying in air-conditioned environments, drinking plenty of water (unless on fluid restriction), and monitoring for swelling or dizziness. — Your Vector-AYU Care Team",
        es: "Se espera calor extremo en Dallas. Si tiene una afección cardíaca o presión arterial alta, el calor extremo obliga a su corazón a trabajar más. Recomendamos permanecer en ambientes con aire acondicionado, beber mucha agua y controlar la hinchazón o mareos. — Su equipo Vector-AYU",
      }
    },
    {
      id: "track_c",
      name: "Extreme Heat — Metabolic Panel",
      trigger: "Heat >100°F",
      population: "438 patients (Track C)",
      track: "C",
      messages: {
        en: "Extreme heat is expected in Dallas over the next 48 hours. If you manage diabetes, remember that heat can cause unpredictable blood sugar spikes and can degrade insulin. Do not leave medication in a hot car, stay hydrated, and protect your feet from hot pavement. — Your Vector-AYU Care Team",
        es: "Se espera calor extremo en Dallas. Si controla la diabetes, recuerde que el calor puede causar picos impredecibles de azúcar en la sangre y degradar la insulina. No deje medicamentos en el auto caliente, manténgase hidratado y proteja sus pies. — Su equipo Vector-AYU",
      }
    }
  ];
};

function OutreachPage() {
  const { data: logs } = useSuspenseQuery(outreachQuery);
  const qc = useQueryClient();
  const [step, setStep] = useState(2);
  const [lang, setLang] = useState<"en" | "es">("en");
  const CAMPAIGNS = getCampaigns();
  const [activeCampaignIdx, setActiveCampaignIdx] = useState(0);
  const activeCampaign = CAMPAIGNS[activeCampaignIdx];
  // Track approval per campaign so they can send both
  const [approvedCampaigns, setApprovedCampaigns] = useState<Record<string, boolean>>({});

  const approveMut = useMutation({
    mutationFn: async () => {
      await insertOutreach({
        patient_id: `TX-COHORT-${activeCampaign.track}`,
        track: activeCampaign.track as any,
        message_content: activeCampaign.messages[lang],
      });
    },
    onSuccess: () => {
      setApprovedCampaigns(prev => ({ ...prev, [activeCampaign.id]: true }));
      setStep(4);
      localStorage.setItem("vayu_consumer_sms", activeCampaign.messages[lang]);
      window.dispatchEvent(new Event("vayu_sms_update"));
      qc.invalidateQueries({ queryKey: ["outreach_logs"] });
    },
  });

  const isApproved = approvedCampaigns[activeCampaign.id];

  return (
    <div className="max-w-[1320px] mx-auto px-7 py-7 flex flex-col gap-6">
      <div className="animate-fade-up flex items-start justify-between">
        <div>
          <h1 className="text-[1.7rem] font-extrabold tracking-tight">48-Hour Approve & Release</h1>
          <p className="text-[0.88rem] text-text-dim mt-1.5">
            Review AI-generated outreach campaigns and approve for delivery to consented patients.
          </p>
        </div>
        <div>
          <select 
            className="px-4 py-2 bg-surface border border-border rounded-lg focus:outline-none focus:border-teal font-semibold"
            value={activeCampaignIdx}
            onChange={(e) => {
              setActiveCampaignIdx(Number(e.target.value));
              setStep(approvedCampaigns[CAMPAIGNS[Number(e.target.value)].id] ? 4 : 2);
            }}
          >
            {CAMPAIGNS.map((c, i) => (
              <option key={c.id} value={i}>{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      <StepperCard>
        <Stepper steps={STEPS} current={step} />
      </StepperCard>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Campaign details */}
        <section className="bg-card border border-border rounded-[14px] p-6 animate-fade-up">
          <h2 className="text-[1rem] font-bold mb-5">📢 Campaign Details</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <Detail label="Campaign" value={activeCampaign.name} full />
            <Detail label="Generated By" value="Vector-AYU AI Worker" />
            <Detail label="Trigger" value={activeCampaign.trigger} />
            <Detail label="Target Population" value={activeCampaign.population} />
            <Detail label="Channel" value={<Tag color="teal">SMS</Tag>} />
            <Detail label="Priority" value={<Tag color="coral">Critical</Tag>} />
          </div>
        </section>

        {/* Approval */}
        <section className="bg-card border border-border rounded-[14px] p-6 animate-fade-up">
          <h2 className="text-[1rem] font-bold mb-5">🔐 Approval Controls</h2>
          <div className="flex items-center gap-3 mb-5">
            <label className="text-[0.78rem] font-semibold text-text-dim whitespace-nowrap">
              Schedule:
            </label>
            <select className="flex-1 px-3.5 py-2.5 rounded-lg bg-surface border border-border text-sm focus:outline-none focus:border-teal">
              <option>Immediate</option>
              <option>In 30 minutes</option>
              <option>Tomorrow at 8:00 AM</option>
            </select>
          </div>
          <button
            onClick={() => approveMut.mutate()}
            disabled={isApproved || approveMut.isPending}
            className={`w-full px-5 py-3.5 rounded-xl font-bold text-[0.95rem] transition-all flex items-center justify-center gap-2 ${
              isApproved
                ? "bg-teal/20 text-teal border border-teal cursor-default"
                : "bg-gradient-to-r from-teal to-[#00b894] text-[#0a0f1e] hover:shadow-[0_8px_30px_rgba(0,212,170,0.4)] hover:-translate-y-px"
            }`}
          >
            {isApproved ? (
              <>
                <Check className="w-5 h-5" /> Approved · Sent to {activeCampaign.population.split(" ")[0]} patients
              </>
            ) : approveMut.isPending ? (
              "Sending..."
            ) : (
              "✓ Approve & Schedule Campaign"
            )}
          </button>
          <div className="mt-4 px-4 py-3 rounded-lg bg-blue/[0.06] border border-blue/15 text-[0.78rem] text-blue flex items-start gap-2.5">
            <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span>
              FHIR Progress Note will be automatically documented for all {activeCampaign.population.split(" ")[0]} patients upon delivery
              confirmation.
            </span>
          </div>
        </section>
      </div>

      {/* Message preview */}
      <section className="bg-card border border-border rounded-[14px] p-6 animate-fade-up">
        <h2 className="text-[1rem] font-bold mb-5">💬 Message Preview</h2>
        <div className="flex justify-center mb-4">
          <div className="inline-flex border border-border rounded-lg overflow-hidden">
            {(["en", "es"] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                className={`px-5 py-2 text-[0.78rem] font-semibold transition ${
                  lang === l ? "bg-teal-dim text-teal" : "text-text-dim hover:bg-white/[0.03]"
                }`}
              >
                {l === "en" ? "🇺🇸 English" : "🇪🇸 Español"}
              </button>
            ))}
          </div>
        </div>
        <div className="max-w-md mx-auto bg-surface border border-border rounded-2xl p-5">
          <div className="flex items-center gap-3 pb-3 border-b border-border">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-teal to-blue flex items-center justify-center text-xs font-bold text-[#0a0f1e]">
              VA
            </div>
            <div>
              <div className="text-[0.85rem] font-semibold">Vector-AYU</div>
              <div className="text-[0.68rem] text-text-muted">SMS · Now</div>
            </div>
          </div>
          <div className="mt-3 p-4 rounded-2xl bg-teal/[0.06] border border-teal/15 text-[0.82rem] leading-relaxed">
            {activeCampaign.messages[lang]}
          </div>
          <div className="text-[0.66rem] text-text-muted text-right mt-2">Today, 2:24 PM CDT</div>
        </div>
      </section>

      {/* History */}
      <section className="bg-card border border-border rounded-[14px] p-6 animate-fade-up">
        <h2 className="text-[1rem] font-bold mb-4">📋 Outreach History Log</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="text-[0.68rem] uppercase tracking-wider text-text-dim border-b border-border">
                <th className="text-left px-4 py-2.5">Sent At</th>
                <th className="text-left px-4 py-2.5">Patient</th>
                <th className="text-left px-4 py-2.5">Track</th>
                <th className="text-left px-4 py-2.5">Message</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr
                  key={l.id}
                  className="border-b border-border last:border-0 hover:bg-white/[0.02]"
                >
                  <td className="px-4 py-3 text-text-dim">
                    {new Date(l.sent_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-semibold text-teal">{l.patient_id}</td>
                  <td className="px-4 py-3">
                    <Tag color={l.track === "A" ? "teal" : "amber"}>Track {l.track}</Tag>
                  </td>
                  <td className="px-4 py-3 text-text-dim truncate max-w-md">{l.message_content}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Detail({ label, value, full }: { label: string; value: React.ReactNode; full?: boolean }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <div className="text-[0.66rem] uppercase tracking-wider text-text-muted font-semibold mb-1">
        {label}
      </div>
      <div className="text-[0.88rem] font-semibold">{value}</div>
    </div>
  );
}

function Tag({
  children,
  color,
}: {
  children: React.ReactNode;
  color: "teal" | "amber" | "coral";
}) {
  const c = { teal: "#00d4aa", amber: "#ffb347", coral: "#ff6b6b" }[color];
  return (
    <span
      className="text-[0.68rem] font-semibold px-2 py-0.5 rounded"
      style={{ background: `${c}1f`, color: c }}
    >
      {children}
    </span>
  );
}
