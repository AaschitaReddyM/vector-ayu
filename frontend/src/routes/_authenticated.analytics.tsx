import { createFileRoute } from "@tanstack/react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DollarSign, HeartPulse, MessageSquare, ShieldCheck } from "lucide-react";
import { StatCard } from "@/components/vayu/StatCard";
import { ANALYTICS_INTERVENTIONS, ED_UTILIZATION, RISK_TIER_DIST } from "@/lib/mock-data";

export const Route = createFileRoute("/_authenticated/analytics")({
  head: () => ({ meta: [{ title: "Vector-AYU — Population Health Analytics" }] }),
  component: AnalyticsPage,
  errorComponent: ({ error }) => <div className="p-10 text-coral">{error.message}</div>,
  notFoundComponent: () => <div className="p-10">Not found</div>,
});

const TOOLTIP_STYLE = {
  background: "rgba(17,24,39,0.95)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 10,
  color: "#f0f4f8",
  fontSize: 12,
};

function AnalyticsPage() {
  const totalPreventable = ED_UTILIZATION.reduce((acc, d) => acc + (d.predicted - d.actual), 0);

  return (
    <div className="max-w-[1440px] mx-auto px-7 py-7 flex flex-col gap-6">
      <div className="animate-fade-up">
        <h1 className="text-[1.7rem] font-extrabold tracking-tight">
          📊 Population Health Intelligence
        </h1>
        <p className="text-[0.88rem] text-text-dim mt-1.5">
          ROI · ED visits prevented · Engagement · DFW Metro Cohort
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          label="ED Visits Prevented"
          value={totalPreventable.toLocaleString()}
          sub="30-day rolling · $2,500 each"
          accent="coral"
          icon={<HeartPulse className="w-5 h-5" />}
        />
        <StatCard
          label="Estimated Savings"
          value="$2.1M"
          sub="At $2,500 per avoided ED visit"
          accent="teal"
          icon={<DollarSign className="w-5 h-5" />}
        />
        <StatCard
          label="Interventions Sent"
          value="3,241"
          sub="This month · 98.2% delivered"
          accent="blue"
          icon={<MessageSquare className="w-5 h-5" />}
        />
        <StatCard
          label="Patient Engagement"
          value="73%"
          sub="SMS response · Track A"
          accent="purple"
          icon={<ShieldCheck className="w-5 h-5" />}
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Interventions */}
        <ChartCard title="📈 Interventions Over Time" sub="Last 14 days">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ANALYTICS_INTERVENTIONS}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="day"
                tick={{ fill: "#8892a4", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis tick={{ fill: "#8892a4", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "rgba(0,212,170,0.05)" }} />
              <Bar dataKey="count" fill="#00d4aa" fillOpacity={0.85} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Risk tier doughnut */}
        <ChartCard title="🎯 Risk Tier Distribution" sub="Active patient population">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={RISK_TIER_DIST}
                dataKey="value"
                nameKey="name"
                innerRadius={70}
                outerRadius={110}
                paddingAngle={3}
                strokeWidth={0}
              >
                {RISK_TIER_DIST.map((d) => (
                  <Cell key={d.name} fill={d.color} fillOpacity={0.85} />
                ))}
              </Pie>
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend
                verticalAlign="bottom"
                iconType="circle"
                wrapperStyle={{ fontSize: 11, color: "#8892a4" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* ED Utilization */}
      <ChartCard title="🏥 ED Utilization: Predicted vs Actual" sub="30-day rolling window">
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={ED_UTILIZATION}>
            <CartesianGrid stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="day"
              tick={{ fill: "#8892a4", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis tick={{ fill: "#8892a4", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 11, color: "#8892a4" }} />
            <Line
              type="monotone"
              dataKey="predicted"
              name="Predicted (no intervention)"
              stroke="#ff6b6b"
              strokeWidth={2.5}
              strokeDasharray="6 4"
              dot={false}
              activeDot={{ r: 5 }}
            />
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual (with Vector-AYU)"
              stroke="#00d4aa"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ROI box */}
      <section className="bg-gradient-to-br from-teal/[0.06] to-blue/[0.06] border border-teal/20 rounded-[14px] p-7 animate-fade-up">
        <h2 className="text-[1.1rem] font-bold mb-2">💼 Enterprise ROI Snapshot</h2>
        <p className="text-[0.85rem] text-text-dim mb-5">
          B2B SaaS for Medicare Advantage Plans, ACOs, and risk-bearing healthcare orgs.
        </p>
        <div className="grid md:grid-cols-3 gap-4">
          <RoiCard label="Projected Annual Savings" value="$4.2M" color="#00d4aa" />
          <RoiCard label="Vector-AYU Annual Cost" value="$510K" color="#4ea8de" />
          <RoiCard label="Net ROI" value="723%" color="#ffb347" highlight />
        </div>
      </section>
    </div>
  );
}

function ChartCard({
  title,
  sub,
  children,
}: {
  title: string;
  sub: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-card border border-border rounded-[14px] overflow-hidden hover-lift animate-fade-up">
      <header className="px-5 py-4 border-b border-border flex items-center justify-between">
        <h3 className="text-[0.95rem] font-semibold">{title}</h3>
        <span className="text-[0.72rem] text-text-muted">{sub}</span>
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

function RoiCard({
  label,
  value,
  color,
  highlight,
}: {
  label: string;
  value: string;
  color: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`p-5 rounded-xl border ${highlight ? "border-teal/40 bg-teal/[0.08]" : "border-border bg-white/[0.02]"}`}
    >
      <div className="text-[0.7rem] uppercase tracking-wider text-text-muted font-semibold mb-2">
        {label}
      </div>
      <div className="text-[1.8rem] font-extrabold tracking-tight" style={{ color }}>
        {value}
      </div>
    </div>
  );
}
