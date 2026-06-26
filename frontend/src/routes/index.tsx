import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { signIn } from "@/lib/auth";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Vector-AYU — SMART on FHIR Login" },
      {
        name: "description",
        content: "Vector-AYU population-health intelligence: connect via SMART on FHIR.",
      },
    ],
  }),
  component: LoginPage,
});

const HOSPITALS = [
  { id: "parkland", name: "Parkland Health — Dallas" },
  { id: "utsw", name: "UT Southwestern Medical Center" },
  { id: "baylor", name: "Baylor Scott & White Health" },
  { id: "texashealth", name: "Texas Health Resources" },
];

const STEPS = [
  { label: "Establishing secure OAuth 2.0 tunnel...", sub: "TLS 1.3 handshake · 256-bit AES" },
  {
    label: "Authenticating provider credentials...",
    sub: "Provider DR-AMO-2847 · Scope: patient/*.read",
  },
  { label: "Loading FHIR Resources...", sub: "2,847 patients · 48,291 observations synced" },
  { label: "Launching Vector-AYU Layer...", sub: "Multi-Task AI · 3 prediction heads active" },
];

function LoginPage() {
  const navigate = useNavigate();
  const [connecting, setConnecting] = useState(false);
  const [step, setStep] = useState(-1);

  useEffect(() => {
    if (!connecting) return;
    const timers: ReturnType<typeof setTimeout>[] = [];
    STEPS.forEach((_, i) => {
      timers.push(setTimeout(() => setStep(i), 600 + i * 700));
    });
    timers.push(
      setTimeout(
        () => {
          signIn();
          navigate({ to: "/dashboard" });
        },
        600 + STEPS.length * 700 + 400,
      ),
    );
    return () => timers.forEach(clearTimeout);
  }, [connecting, navigate]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden px-5 py-10">
      {/* Orbs */}
      <div
        className="fixed w-[600px] h-[600px] rounded-full blur-[120px] opacity-[0.18] pointer-events-none -top-[150px] -left-[100px]"
        style={{
          background: "radial-gradient(circle, #00d4aa, transparent 70%)",
          animation: "orbFloat1 18s ease-in-out infinite",
        }}
      />
      <div
        className="fixed w-[500px] h-[500px] rounded-full blur-[120px] opacity-[0.18] pointer-events-none -bottom-[100px] -right-[80px]"
        style={{
          background: "radial-gradient(circle, #4ea8de, transparent 70%)",
          animation: "orbFloat2 22s ease-in-out infinite",
        }}
      />
      {/* Grid overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-60"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,.015) 1px,transparent 1px), linear-gradient(90deg,rgba(255,255,255,.015) 1px,transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      <div className="relative z-10 w-full max-w-[520px] animate-fade-up">
        {/* Hero */}
        <div className="text-center mb-10">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl flex items-center justify-center bg-white border border-teal/30 shadow-[0_8px_40px_rgba(0,212,170,0.2)]">
            <img src="/logo.jpeg" alt="Vector-AYU Logo" className="w-16 h-16 object-contain" />
          </div>
          <h1 className="text-[2.5rem] font-extrabold tracking-tight text-gradient-brand">
            Vector-AYU
          </h1>
          <p className="text-text-dim mt-2 text-sm">Population Health Intelligence · DFW Metro</p>
        </div>

        {/* Card */}
        <div className="bg-card/80 backdrop-blur-xl border border-border rounded-2xl p-7 shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
          <div className="flex items-center gap-2 text-[0.72rem] text-teal font-semibold uppercase tracking-wider mb-5">
            <span className="w-2 h-2 rounded-full bg-teal animate-pulse-dot" />
            SMART on FHIR Launch Sequence
          </div>

          <div className="space-y-4">
            <Field label="Hospital System">
              <select className="w-full px-3.5 py-2.5 rounded-lg bg-surface border border-border text-foreground text-sm focus:outline-none focus:border-teal transition">
                {HOSPITALS.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Provider ID">
              <input
                readOnly
                value="DR-AMO-2847"
                className="w-full px-3.5 py-2.5 rounded-lg bg-surface border border-border text-teal text-sm font-medium"
              />
            </Field>

            <div className="bg-white/[0.02] border border-border rounded-xl p-4 flex items-center gap-3">
              <div className="w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold text-[#0a0f1e] bg-gradient-to-br from-teal to-blue">
                AO
              </div>
              <div>
                <div className="font-semibold text-sm">Dr. Amara Okafor, MD</div>
                <div className="text-[0.72rem] text-teal">Pulmonology & Internal Medicine</div>
                <div className="text-[0.7rem] text-text-muted">
                  Parkland Health — DFW Metro Network
                </div>
              </div>
            </div>

            <button
              onClick={() => setConnecting(true)}
              disabled={connecting}
              className="relative w-full px-4 py-3.5 rounded-xl text-[0.95rem] font-bold text-[#0a0f1e] bg-gradient-to-r from-teal to-[#00b894] hover:shadow-[0_8px_30px_rgba(0,212,170,0.4)] transition-all disabled:opacity-60 disabled:cursor-not-allowed overflow-hidden"
            >
              {connecting ? "Connecting…" : "Connect via SMART on FHIR"}
            </button>

            <div className="grid grid-cols-2 gap-2 pt-2">
              {[
                { i: "🛡️", l: "HIPAA Compliant" },
                { i: "🔒", l: "SOC 2 Type II" },
                { i: "🔐", l: "TLS 1.3 Encrypted" },
                { i: "🏥", l: "HL7 FHIR v4" },
              ].map((b) => (
                <div
                  key={b.l}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-border text-[0.7rem] text-text-dim"
                >
                  <span>{b.i}</span>
                  <span className="font-medium">{b.l}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-[0.72rem] text-text-muted mt-5">
          Vector-AYU Layer v2.4.1 · DFW Metro Region
        </p>
      </div>

      {/* Connection overlay */}
      {connecting && (
        <div className="fixed inset-0 z-[200] bg-background/85 backdrop-blur-xl flex items-center justify-center px-5 animate-fade-up">
          <div className="max-w-[480px] w-full bg-card border border-border rounded-2xl p-8">
            <div className="flex items-center gap-3 mb-6">
              <svg viewBox="0 0 32 32" className="w-9 h-9" fill="none">
                <circle cx="16" cy="16" r="14" stroke="url(#og)" strokeWidth="2.5" />
                <path d="M16 8v8l6 4" stroke="url(#og)" strokeWidth="2.2" strokeLinecap="round" />
                <defs>
                  <linearGradient id="og" x1="0" y1="0" x2="32" y2="32">
                    <stop stopColor="#00d4aa" />
                    <stop offset="1" stopColor="#4ea8de" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="font-bold text-lg">
                VAY<span className="text-teal">U</span>
              </div>
            </div>
            <div className="space-y-4">
              {STEPS.map((s, i) => {
                const done = step >= i + 1 || (step === STEPS.length - 1 && i === STEPS.length - 1);
                const loading = step === i;
                return (
                  <div
                    key={i}
                    className={`flex items-start gap-3 transition-opacity ${
                      step >= i ? "opacity-100" : "opacity-30"
                    }`}
                  >
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 border ${
                        done
                          ? "bg-teal/10 border-teal text-teal"
                          : loading
                            ? "border-teal text-teal animate-pulse-dot"
                            : "border-border text-text-muted"
                      }`}
                    >
                      {done ? "✓" : loading ? "⋯" : "•"}
                    </div>
                    <div>
                      <div className="text-[0.88rem] font-medium">{s.label}</div>
                      <div className="text-[0.72rem] text-text-muted mt-0.5">{s.sub}</div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="h-1 mt-6 rounded-full bg-white/[0.05] overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-teal to-blue transition-all duration-500"
                style={{ width: `${Math.max(0, ((step + 1) / STEPS.length) * 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[0.72rem] font-semibold uppercase tracking-wider text-text-dim mb-1.5">
        {label}
      </label>
      {children}
    </div>
  );
}
