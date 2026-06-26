import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Driver = {
  label: string;
  stream: "environmental" | "clinical" | "static";
  value: number;
};

const STREAM_COLORS: Record<string, string> = {
  environmental: "#4ea8de",
  clinical: "#00d4aa",
  static: "#a78bfa",
};

export function XaiBars({ drivers }: { drivers: Driver[] }) {
  const sorted = [...drivers].sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={sorted}
          layout="vertical"
          margin={{ top: 8, right: 20, left: 8, bottom: 8 }}
        >
          <XAxis
            type="number"
            domain={[-1, 1]}
            tick={{ fill: "#8892a4", fontSize: 11 }}
            axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={150}
            tick={{ fill: "#c8cdd5", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
            contentStyle={{
              background: "rgba(17,24,39,0.95)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 10,
              color: "#f0f4f8",
              fontSize: 12,
            }}
            formatter={(v: number) => [`${v > 0 ? "+" : ""}${v.toFixed(2)}`, "SHAP"]}
          />
          <Bar dataKey="value" radius={[4, 4, 4, 4]} barSize={16}>
            {sorted.map((d, i) => {
              const isRisk = d.value >= 0;
              const base = STREAM_COLORS[d.stream] ?? "#4ea8de";
              return (
                <Cell key={i} fill={isRisk ? "#ff6b6b" : base} fillOpacity={isRisk ? 0.78 : 0.65} />
              );
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 text-[0.7rem] text-text-muted justify-end mt-2">
        <Legend color="#ff6b6b" label="Risk-increasing" />
        <Legend color="#4ea8de" label="Environmental" />
        <Legend color="#00d4aa" label="Clinical" />
        <Legend color="#a78bfa" label="Static" />
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}
