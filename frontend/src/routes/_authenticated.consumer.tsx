import { createFileRoute } from "@tanstack/react-router";
import { PhoneFrame } from "@/components/vayu/PhoneFrame";
import { NudgeAlert } from "@/components/vayu/NudgeAlert";
import { RiskRing } from "@/components/vayu/RiskRing";

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

const TONE_COLORS = { amber: "#ffb347", coral: "#ff6b6b", teal: "#00d4aa" };

function ConsumerPage() {
  return (
    <div className="max-w-[1440px] mx-auto px-7 py-7 flex flex-col items-center gap-6">
      <div className="text-center animate-fade-up">
        <h1 className="text-[1.7rem] font-extrabold tracking-tight">📱 Consumer App Preview</h1>
        <p className="text-[0.88rem] text-text-dim mt-1.5">
          Your personalized Health-Weather Score · Patient-facing iOS preview
        </p>
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
              <div className="text-[1.35rem] font-bold mt-0.5">Maria Garcia 👋</div>
              <div className="text-[0.72rem] text-text-dim mt-1">📍 Dallas, TX 75201</div>
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
          <div className="text-[0.78rem] font-semibold uppercase tracking-wider text-text-dim mb-3">
            Daily Behavioral Nudges
          </div>
          <div className="flex flex-col gap-3">
            <NudgeAlert
              icon="💧"
              title="Hydrate More"
              tone="blue"
              description="Heat index reaching 103°F. Aim for 10+ glasses today."
            />
            <NudgeAlert
              icon="🫁"
              title="Stay Indoors After 2 PM"
              tone="coral"
              description="Ozone levels peak in afternoon. Move workouts to early AM."
            />
            <NudgeAlert
              icon="💊"
              title="Medication Reminder"
              tone="purple"
              description="Barometric pressure dropping tonight. Take evening meds by 6 PM."
            />
            <NudgeAlert
              icon="🏠"
              title="Air Quality Alert"
              tone="amber"
              description="AQI at 207. Keep windows closed; run an air purifier."
            />
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
