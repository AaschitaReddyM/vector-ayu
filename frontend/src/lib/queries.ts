import { queryOptions } from "@tanstack/react-query";
import { isSupabaseConfigured, supabase } from "./supabase";
import {
  MOCK_OUTREACH,
  MOCK_PATIENTS,
  MOCK_RISK_SCORES,
  MOCK_TRIAGE,
  type OutreachLog,
  type Patient,
  type RiskScore,
  type TriageEntry,
} from "./mock-data";

export const patientsQuery = queryOptions({
  queryKey: ["patients"],
  queryFn: async (): Promise<Patient[]> => {
    let pts = MOCK_PATIENTS;
    if (typeof window !== "undefined") {
        const isNewDelhi = localStorage.getItem("vayu_region") === "new_delhi";
        if (isNewDelhi) pts = MOCK_PATIENTS.slice(12, 24);
        else pts = MOCK_PATIENTS.slice(0, 12);
    }
    
    if (!isSupabaseConfigured || !supabase) return pts;
    const { data, error } = await supabase.from("patients").select("*");
    if (error || !data || data.length === 0) return pts;
    return data as Patient[];
  },
});

export const patientQuery = (id: string) =>
  queryOptions({
    queryKey: ["patient", id],
    queryFn: async (): Promise<Patient | null> => {
      if (!isSupabaseConfigured || !supabase)
        return MOCK_PATIENTS.find((p) => p.id === id) ?? MOCK_PATIENTS[0];
      const { data } = await supabase.from("patients").select("*").eq("id", id).maybeSingle();
      return (data as Patient | null) ?? MOCK_PATIENTS.find((p) => p.id === id) ?? null;
    },
  });

export const riskScoresQuery = queryOptions({
  queryKey: ["risk_scores"],
  queryFn: async (): Promise<RiskScore[]> => {
    if (!isSupabaseConfigured || !supabase) return MOCK_RISK_SCORES;
    const { data, error } = await supabase
      .from("risk_scores")
      .select("*")
      .order("scored_at", { ascending: false });
    if (error || !data || data.length === 0) return MOCK_RISK_SCORES;
    return data as RiskScore[];
  },
});

export const riskScoreQuery = (patientId: string) =>
  queryOptions({
    queryKey: ["risk_score", patientId],
    queryFn: async (): Promise<RiskScore | null> => {
      if (!isSupabaseConfigured || !supabase)
        return MOCK_RISK_SCORES.find((r) => r.patient_id === patientId) ?? null;
      const { data } = await supabase
        .from("risk_scores")
        .select("*")
        .eq("patient_id", patientId)
        .order("scored_at", { ascending: false })
        .limit(1)
        .maybeSingle();
      return (
        (data as RiskScore | null) ??
        MOCK_RISK_SCORES.find((r) => r.patient_id === patientId) ??
        null
      );
    },
  });

export const triageQuery = queryOptions({
  queryKey: ["triage_queue"],
  queryFn: async (): Promise<TriageEntry[]> => {
    if (!isSupabaseConfigured || !supabase) {
      // Fetch from local FastAPI backend
      try {
        const apiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiUrl}/api/triage/queue`);
        if (res.ok) {
          const data = await res.json();
          const entries: TriageEntry[] = [];
          data.accepted.forEach((f: any) => {
            entries.push({
              id: `tq-${f.patient_id}`,
              patient_id: f.patient_id,
              risk_total: Math.round(f.risk_total * 100),
              head: f.head,
              status: "accepted",
              triage_date: new Date().toISOString()
            });
          });
          data.deferred.forEach((f: any) => {
            entries.push({
              id: `tq-${f.patient_id}`,
              patient_id: f.patient_id,
              risk_total: Math.round(f.risk_total * 100),
              head: f.head,
              status: "deferred",
              triage_date: new Date().toISOString()
            });
          });
          // Also patch in the combined_delta from riskScores to match the frontend expectations?
          // The frontend dashboard relies on scores.combined_delta. 
          return entries;
        }
      } catch (err) {
        console.error("Failed to fetch triage queue from backend, falling back to static mock", err);
      }
      return MOCK_TRIAGE;
    }
    const { data, error } = await supabase
      .from("triage_queue")
      .select("*")
      .order("risk_total", { ascending: false });
    if (error || !data || data.length === 0) return MOCK_TRIAGE;
    return data as TriageEntry[];
  },
});

export const outreachQuery = queryOptions({
  queryKey: ["outreach_logs"],
  queryFn: async (): Promise<OutreachLog[]> => {
    if (!isSupabaseConfigured || !supabase) return MOCK_OUTREACH;
    const { data, error } = await supabase
      .from("outreach_logs")
      .select("*")
      .order("sent_at", { ascending: false });
    if (error || !data) return MOCK_OUTREACH;
    return data as OutreachLog[];
  },
});

export async function insertOutreach(log: Omit<OutreachLog, "id" | "sent_at">): Promise<void> {
  if (!isSupabaseConfigured || !supabase) {
    MOCK_OUTREACH.unshift({
      ...log,
      id: `ol-${Date.now()}`,
      sent_at: new Date().toISOString(),
    });
    return;
  }
  await supabase.from("outreach_logs").insert({ ...log, sent_at: new Date().toISOString() });
}
