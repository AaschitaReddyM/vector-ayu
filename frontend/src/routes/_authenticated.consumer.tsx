import { createFileRoute } from "@tanstack/react-router";
import { PhoneFrame } from "@/components/vayu/PhoneFrame";
import { NudgeAlert } from "@/components/vayu/NudgeAlert";
import { RiskRing } from "@/components/vayu/RiskRing";
import { useState, useEffect } from "react";

export const Route = createFileRoute("/_authenticated/consumer")({
  head: () => ({ meta: [{ title: "Vector-AYU — Consumer Health-Weather Score" }] }),
  component: ConsumerPage,
  errorComponent: ({ error }) => <div className="p-10 text-coral">{error.message}</div>,
  notFoundComponent: () => <div className="p-10">Not found</div>,
});

const FORECAST = [
  { day: "Today", weather: "⛅", info: "Partly Cloudy · 98°F", score: 72, tone: "amber" as const },
  {
    day: "Tomorrow",
    weather: "🌩️",
    info: "Thunderstorms · 94°F",
    score: 58,
    tone: "coral" as const,
  },
  { day: "Thursday", weather: "☀️", info: "Sunny · 92°F", score: 81, tone: "teal" as const },
];

const CONSUMERS = [
  {
    id: "maria",
    name: "Maria Hernandez",
    zip: "75201",
    cohort: "Track B (Cardiovascular)",
    nudges: [
      { icon: "💧", title: "Hydrate More", tone: "blue", description: "Heat index reaching 103°F. Aim for 10+ glasses today." },
      { icon: "🫀", title: "Monitor Swelling", tone: "coral", description: "Extreme heat increases strain on your heart. Watch for edema." },
      { icon: "💊", title: "Medication Reminder", tone: "purple", description: "Barometric pressure dropping tonight. Take evening meds by 6 PM." }
    ]
  },
  {
    id: "lin",
    name: "Lin Rodriguez",
    zip: "75205",
    cohort: "Track A (Respiratory)",
    nudges: [
      { icon: "🫁", title: "Inhaler Check", tone: "coral", description: "Ozone levels peak in afternoon. Keep your rescue inhaler accessible." },
      { icon: "🏠", title: "Air Quality Alert", tone: "amber", description: "AQI at 207. Keep windows closed; run an air purifier." },
      { icon: "🌡️", title: "Stay Cool", tone: "blue", description: "Heat triggers asthma. Keep indoor temp below 76°F." }
    ]
  },
  {
    id: "eleanor",
    name: "Eleanor Vance",
    zip: "75200",
    cohort: "Track C (Metabolic)",
    nudges: [
      { icon: "🩸", title: "Blood Sugar Check", tone: "amber", description: "Heat can cause glucose spikes. Check your levels at noon." },
      { icon: "🧊", title: "Keep Insulin Cool", tone: "blue", description: "Temperatures exceeding 95°F today. Do not leave insulin in the car." },
      { icon: "👟", title: "Foot Care", tone: "coral", description: "Do not walk barefoot outside, pavement temperatures are dangerously high." }
    ]
  }
];

const TONE_COLORS = { amber: "#ffb347", coral: "#ff6b6b", teal: "#00d4aa", blue: "#4ea8de", purple: "#9d4edd" };

function ConsumerPage() {
  const liveSms = typeof window !== 'undefined' ? localStorage.getItem("vayu_consumer_sms") : null;
  const [activeConsumerIdx, setActiveConsumerIdx] = useState(0);
  const activeConsumer = CONSUMERS[activeConsumerIdx];

  useEffect(() => {
    // Listen for cross-tab updates (if the doctor approves in another window)
    const handleStorage = () => {
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  // For cross-tab reactivity without complex state management in this demo:
  const [, setTick] = useState(0);
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === "vayu_consumer_sms") setTick(t => t + 1);
    };
    window.addEventListener("storage", handleStorage);
    // Also listen to a custom event for same-tab updates
    window.addEventListener("vayu_sms_update", () => setTick(t => t + 1));
    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("vayu_sms_update", () => setTick(t => t + 1));
    };
  }, []);

  return (
    <div className="max-w-[1440px] mx-auto px-7 py-7 flex flex-col items-center gap-6">
      <div className="text-center animate-fade-up">
        <h1 className="text-[1.7rem] font-extrabold tracking-tight">📱 Consumer App Preview</h1>
        <p className="text-[0.88rem] text-text-dim mt-1.5 mb-4">
          Your personalized Health-Weather Score · Patient-facing iOS preview
        </p>
        
        <div className="flex items-center gap-3 justify-center mb-6">
          <span className="text-sm font-semibold text-text-muted">Viewing as:</span>
          <select 
            className="px-4 py-2 bg-card border border-border rounded-lg focus:outline-none focus:border-teal font-semibold text-sm"
            value={activeConsumerIdx}
            onChange={(e) => setActiveConsumerIdx(Number(e.target.value))}
          >
            {CONSUMERS.map((c, i) => (
              <option key={c.id} value={i}>{c.name} — {c.cohort}</option>
            ))}
          </select>
        </div>
      </div>

      <PhoneFrame>
        {/* Header */}
        <div className="px-6 pt-12 pb-6 relative overflow-hidden bg-gradient-to-br from-[#0d2847] via-[#0a3040] to-[#0f1f30]">
          <div
            className="absolute -top-20 -right-16 w-64 h-64 rounded-full opacity-50 pointer-events-none"
            style={{ background: "radial-gradient(circle,rgba(0,212,170,0.18),transparent 70%)" }}
          />
          <div className="flex justify-between items-start relative">
            <div>
              <div className="text-[0.75rem] text-text-muted">Good Morning,</div>
              <div className="text-[1.35rem] font-bold mt-0.5">{activeConsumer.name.split(" ")[0]} 👋</div>
              <div className="text-[0.72rem] text-text-dim mt-1">📍 Dallas, TX {activeConsumer.zip}</div>
            </div>
            <div className="text-[0.7rem] text-text-dim text-right leading-relaxed">
              Wed, May 28
              <br />
              8:42 AM
            </div>
          </div>
        </div>

        {/* Score */}
        <div className="px-6 -mt-6 flex flex-col items-center">
          <div className="relative bg-card rounded-2xl p-6 border border-border shadow-[0_8px_30px_rgba(0,0,0,0.3)] w-full">
            <div className="flex justify-center mb-3">
              <RiskRing value={0.72} size={180} color="#ffb347" label="Vector-AYU Index" />
            </div>
            <div className="text-center">
              <div className="text-[0.78rem] font-semibold text-amber">
                ⛅ Moderate — Take Precautions
              </div>
              <div className="text-[0.72rem] text-text-muted mt-1">↓ 6 from yesterday</div>
            </div>
          </div>
        </div>

        {/* Nudges */}
        <div className="px-6 mt-6">
          <div className="text-[0.78rem] font-semibold uppercase tracking-wider text-text-dim mb-3 flex items-center justify-between">
            <span>Daily Behavioral Nudges</span>
            {liveSms && (
              <span className="text-[0.6rem] bg-coral/20 text-coral px-2 py-0.5 rounded-full font-bold animate-pulse">
                NEW MESSAGE
              </span>
            )}
          </div>
          <div className="flex flex-col gap-3">
            {liveSms && (
              <div className="animate-fade-up">
                <NudgeAlert
                  icon="💬"
                  title="New SMS from Dr. Rivera"
                  tone="coral"
                  description={liveSms}
                />
              </div>
            )}
            
            {activeConsumer.nudges.map((nudge, i) => (
              <NudgeAlert
                key={i}
                icon={nudge.icon}
                title={nudge.title}
                tone={nudge.tone as any}
                description={nudge.description}
              />
            ))}
          </div>
        </div>

        {/* 3-Day Forecast */}
        <div className="px-6 mt-6">
          <div className="text-[0.78rem] font-semibold uppercase tracking-wider text-text-dim mb-3">
            48-Hour Health Forecast
          </div>
          <div className="flex flex-col gap-2.5">
            {FORECAST.map((f) => (
              <div
                key={f.day}
                className="bg-card border border-border rounded-xl px-4 py-3 flex items-center justify-between hover-lift"
              >
                <div className="flex items-center gap-3">
                  <div className="text-xl">{f.weather}</div>
                  <div>
                    <div className="text-[0.82rem] font-medium">{f.day}</div>
                    <div className="text-[0.62rem] text-text-muted mt-0.5">{f.info}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2.5">
                  <div className="text-[1rem] font-bold" style={{ color: TONE_COLORS[f.tone] }}>
                    {f.score}
                  </div>
                  <span
                    className="text-[0.6rem] font-semibold px-2.5 py-1 rounded-md"
                    style={{ background: `${TONE_COLORS[f.tone]}22`, color: TONE_COLORS[f.tone] }}
                  >
                    {f.tone === "teal" ? "Good" : f.tone === "amber" ? "Moderate" : "Elevated"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </PhoneFrame>
    </div>
  );
}
