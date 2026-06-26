import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Point = { label: string; risk: number; threshold: number };

export function RiskTrajectoryChart({ data }: { data: Point[] }) {
  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
          <defs>
            <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ff6b6b" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#ff6b6b" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.04)" />
          <XAxis
            dataKey="label"
            tick={{ fill: "#8892a4", fontSize: 11 }}
            axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: "#8892a4", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "rgba(17,24,39,0.95)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 10,
              color: "#f0f4f8",
              fontSize: 12,
            }}
          />
          <ReferenceLine
            y={85}
            stroke="#ff6b6b"
            strokeDasharray="6 4"
            strokeOpacity={0.5}
            label={{
              value: "Critical 85",
              position: "insideTopRight",
              fill: "#ff6b6b",
              fontSize: 10,
            }}
          />
          <Area
            type="monotone"
            dataKey="risk"
            stroke="#ff6b6b"
            strokeWidth={2.5}
            fill="url(#riskGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
