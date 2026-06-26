import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// To enable live Supabase data, set these via Vite env (.env.local):
//   VITE_SUPABASE_URL=https://xxxxx.supabase.co
//   VITE_SUPABASE_PUBLISHABLE_KEY=eyJhbGciOi... (anon/publishable key)
// Both values are public; do NOT paste a service role key here.
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;

export const supabase: SupabaseClient | null =
  url && key
    ? createClient(url, key, {
        auth: { persistSession: false, autoRefreshToken: false },
      })
    : null;

export const isSupabaseConfigured = supabase !== null;
