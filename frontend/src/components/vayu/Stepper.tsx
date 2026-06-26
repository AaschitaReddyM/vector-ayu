import type { ReactNode } from "react";

type Step = {
  icon: string;
  label: string;
  time?: string;
};

export function Stepper({ steps, current }: { steps: Step[]; current: number }) {
  return (
    <div className="flex items-center justify-between gap-2 overflow-x-auto pb-2">
      {steps.map((s, i) => {
        const state = i < current ? "completed" : i === current ? "active" : "pending";
        return (
          <div key={i} className="flex items-center flex-1 min-w-0 last:flex-initial">
            <div className="flex flex-col items-center gap-1.5 min-w-[110px]">
              <div
                className={`w-11 h-11 rounded-full flex items-center justify-center text-base border-2 transition-all ${
                  state === "completed"
                    ? "bg-teal-dim border-teal text-teal"
                    : state === "active"
                      ? "bg-teal text-[#0a0f1e] border-teal shadow-[0_0_24px_rgba(0,212,170,0.4)] animate-pulse-dot"
                      : "bg-white/[0.02] border-border text-text-muted"
                }`}
              >
                {s.icon}
              </div>
              <div
                className={`text-[0.72rem] font-semibold text-center ${
                  state === "pending" ? "text-text-muted" : "text-foreground"
                }`}
              >
                {s.label}
              </div>
              <div className="text-[0.62rem] text-text-muted">{s.time ?? "—"}</div>
            </div>
            {i < steps.length - 1 && (
              <div
                className={`h-0.5 flex-1 mx-2 rounded ${
                  i < current
                    ? "bg-teal"
                    : i === current - 0
                      ? "bg-gradient-to-r from-teal to-border"
                      : "bg-border"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function StepperCard({ children }: { children: ReactNode }) {
  return (
    <div className="bg-card border border-border rounded-[14px] p-6 animate-fade-up">
      {children}
    </div>
  );
}
