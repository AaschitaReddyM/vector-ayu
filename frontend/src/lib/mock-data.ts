export type Patient = {
  id: string;
  given_name: string;
  family_name: string;
  birth_date: string;
  gender: string;
  postal_code: string;
  primary_language: string;
};

export type RiskScore = {
  id: string;
  patient_id: string;
  probabilities: { respiratory: number; cardiovascular: number; metabolic: number };
  climate_volatility_delta: { respiratory: number; cardiovascular: number; metabolic: number };
  combined_delta: number;
  top_head: "respiratory" | "cardiovascular" | "metabolic";
  scored_at: string;
};

export type TriageEntry = {
  id: string;
  patient_id: string;
  risk_total: number;
  head: string;
  status: "accepted" | "deferred" | "completed";
  triage_date: string;
};

export type OutreachLog = {
  id: string;
  patient_id: string;
  track: "A" | "B";
  message_content: string;
  sent_at: string;
};

const FIRST = [
  "Eleanor",
  "Maria",
  "James",
  "Aisha",
  "Robert",
  "Lin",
  "Carlos",
  "Patricia",
  "Devon",
  "Yusuf",
  "Hannah",
  "Marcus",
];
const LAST = [
  "Vance",
  "Hernandez",
  "Okonkwo",
  "Patel",
  "Chen",
  "Rodriguez",
  "Williams",
  "Nguyen",
  "Brooks",
  "Al-Sayed",
  "Johnson",
  "Reyes",
];
const CONDS = [
  "COPD Stage IV (Very Severe)",
  "COPD Stage III (Severe)",
  "COPD Stage III (Severe)",
  "COPD Stage II (Moderate)",
  "Heart Failure NYHA III",
  "Type 2 Diabetes + CKD",
  "COPD Stage II (Moderate)",
  "Asthma + Hypertension",
];

export const MOCK_PATIENTS: Patient[] = Array.from({ length: 12 }).map((_, i) => ({
  id: `PT-${(i + 1).toString().padStart(4, "0")}`,
  given_name: FIRST[i],
  family_name: LAST[i],
  birth_date: `19${40 + i}-0${(i % 9) + 1}-1${i % 9}`,
  gender: i % 3 === 0 ? "M" : "F",
  postal_code: `752${i.toString().padStart(2, "0")}`,
  primary_language: i % 4 === 0 ? "es" : "en",
}));

export const MOCK_RISK_SCORES: RiskScore[] = MOCK_PATIENTS.map((p, i) => {
  const base = 0.95 - i * 0.06;
  return {
    id: `rs-${p.id}`,
    patient_id: p.id,
    probabilities: {
      respiratory: Math.max(0.15, base),
      cardiovascular: Math.max(0.1, base - 0.18),
      metabolic: Math.max(0.08, base - 0.32),
    },
    climate_volatility_delta: {
      respiratory: Math.max(0.1, 0.92 - i * 0.05),
      cardiovascular: Math.max(0.08, 0.78 - i * 0.05),
      metabolic: Math.max(0.05, 0.6 - i * 0.05),
    },
    combined_delta: +(2.4 - i * 0.18).toFixed(2),
    top_head: "respiratory",
    scored_at: new Date(Date.now() - i * 3600_000).toISOString(),
  };
});

export const MOCK_TRIAGE: TriageEntry[] = MOCK_PATIENTS.map((p, i) => ({
  id: `tq-${p.id}`,
  patient_id: p.id,
  risk_total: Math.round((0.95 - i * 0.06) * 100),
  head: ["respiratory", "cardiovascular", "metabolic"][i % 3],
  status: i < 7 ? "accepted" : i < 10 ? "deferred" : "completed",
  triage_date: new Date(Date.now() - (i * 86400_000) / 4).toISOString(),
}));

export const MOCK_OUTREACH: OutreachLog[] = [
  {
    id: "ol-1",
    patient_id: "PT-0001",
    track: "A",
    message_content: "Heat Advisory — Respiratory cohort. SMS sent.",
    sent_at: new Date(Date.now() - 86400_000).toISOString(),
  },
  {
    id: "ol-2",
    patient_id: "PT-0002",
    track: "A",
    message_content: "Ozone Alert — Full cohort.",
    sent_at: new Date(Date.now() - 2 * 86400_000).toISOString(),
  },
  {
    id: "ol-3",
    patient_id: "PT-0003",
    track: "B",
    message_content: "Manual Outreach — Non-Consented.",
    sent_at: new Date(Date.now() - 3 * 86400_000).toISOString(),
  },
];

export const PATIENT_DRIVERS: Record<
  string,
  { label: string; stream: "environmental" | "clinical" | "static"; value: number }[]
> = Object.fromEntries(
  MOCK_PATIENTS.map((p) => [
    p.id,
    [
      { label: "Ozone (O₃)", stream: "environmental", value: 1.0 },
      { label: "PM2.5", stream: "environmental", value: 0.89 },
      { label: "SpO2 (pulse-ox)", stream: "clinical", value: 0.72 },
      { label: "AQI composite", stream: "environmental", value: 0.64 },
      { label: "COPD severity (GOLD)", stream: "static", value: 0.14 },
      { label: "Smoking pack-years", stream: "static", value: -0.13 },
      { label: "Inhaler actuations", stream: "clinical", value: -0.12 },
      { label: "HVAC density", stream: "static", value: -0.12 },
    ],
  ]),
);

export const PATIENT_CONDITION: Record<string, string> = Object.fromEntries(
  MOCK_PATIENTS.map((p, i) => [p.id, CONDS[i % CONDS.length]]),
);

export const MEDICATIONS = [
  { name: "Tiotropium (Spiriva)", type: "LAMA", typeColor: "blue", adherence: 94 },
  {
    name: "Fluticasone/Vilanterol (Breo Ellipta)",
    type: "ICS/LABA",
    typeColor: "purple",
    adherence: 87,
  },
  { name: "Albuterol (ProAir)", type: "Rescue Inhaler", typeColor: "amber", adherence: null },
  { name: "Prednisone 10mg", type: "Oral Corticosteroid", typeColor: "coral", adherence: null },
  { name: "Lisinopril 20mg", type: "ACE Inhibitor", typeColor: "teal", adherence: 91 },
];

export const RISK_TRAJECTORY = Array.from({ length: 18 }).map((_, i) => ({
  hour: i * 4,
  label: `+${i * 4}h`,
  risk: Math.round(54 + Math.sin(i * 0.5) * 8 + i * 2.3 + (i > 8 ? (i - 8) * 1.4 : 0)),
  threshold: 85,
}));

export const ANALYTICS_INTERVENTIONS = Array.from({ length: 14 }).map((_, i) => ({
  day: `Day ${i + 1}`,
  count: [45, 62, 38, 91, 120, 85, 72, 156, 134, 98, 167, 143, 189, 201][i],
}));

export const ED_UTILIZATION = Array.from({ length: 30 }).map((_, i) => ({
  day: i + 1,
  predicted: Math.round(40 + i * 1.9 + Math.sin(i * 0.8) * 5),
  actual: Math.round(28 + Math.sin(i * 0.6) * 4),
}));

export const RISK_TIER_DIST = [
  { name: "Critical", value: 142, color: "#ff6b6b" },
  { name: "High", value: 384, color: "#ffb347" },
  { name: "Moderate", value: 891, color: "#4ea8de" },
  { name: "Low", value: 1430, color: "#00d4aa" },
];
