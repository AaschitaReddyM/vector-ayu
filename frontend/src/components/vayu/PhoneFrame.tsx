import type { ReactNode } from "react";

export function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div
      className="w-[393px] min-h-[852px] bg-background rounded-[44px] border-[2.5px] border-white/[0.08] overflow-hidden relative"
      style={{
        boxShadow:
          "0 0 0 1px rgba(255,255,255,.03), 0 4px 16px rgba(0,0,0,.3), 0 20px 60px rgba(0,0,0,.5), 0 40px 100px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.06)",
      }}
    >
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[120px] h-[28px] bg-background rounded-b-[18px] z-50 border border-white/[0.04] border-t-0" />
      <div
        className="h-[852px] overflow-y-auto overflow-x-hidden scrollbar-none pb-20"
        style={{ scrollbarWidth: "none" }}
      >
        {children}
      </div>
    </div>
  );
}
