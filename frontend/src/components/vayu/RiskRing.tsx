type Props = {
  value: number; // 0..1
  size?: number;
  label?: string;
  color?: string;
  trackColor?: string;
};

export function RiskRing({
  value,
  size = 120,
  label,
  color = "#ff6b6b",
  trackColor = "rgba(255,255,255,0.06)",
}: Props) {
  const stroke = Math.max(6, size * 0.07);
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(1, Math.max(0, value));
  const offset = circumference * (1 - pct);
  const pctNum = Math.round(pct * 100);

  return (
    <div className="relative inline-flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(.25,.8,.25,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-[1.6rem] font-extrabold tracking-tight" style={{ color }}>
          {pctNum}
        </div>
        {label && (
          <div className="text-[0.6rem] uppercase tracking-wider text-text-muted font-semibold mt-0.5">
            {label}
          </div>
        )}
      </div>
    </div>
  );
}
