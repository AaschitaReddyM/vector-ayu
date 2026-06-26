## VAYU — Build Plan

A premium dark-mode healthcare triage app matching the supplied HTML mockups (analytics, dashboard, patient-detail, outreach, login, consumer). Tech: React (TanStack Start) + TailwindCSS + Recharts + your existing Supabase.

### Design system (from your mockups)

Locked tokens in `src/styles.css`:

- bg `#0a0f1e`, surface `#111827`, card `#1a2235`, card-hover `#1f2a42`
- accents: teal `#00d4aa`, coral `#ff6b6b`, amber `#ffb347`, blue `#4ea8de`, purple `#a78bfa`
- text `#f0f4f8` / dim `#8892a4` / muted `#5a6478`
- radius 14px, glassmorphism topbar (`backdrop-blur`), Inter via `@fontsource-variable/inter`
- Micro-animations: card hover lift, ring/bar count-up, fade-in-up on mount, animated orbs on login

### Supabase wiring (your project)

1. I'll ask you to paste your Supabase **URL** + **publishable/anon key** via `add_secret` (stored as `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`).
2. Create `src/integrations/supabase/client.ts` browser client.
3. Typed query hooks (TanStack Query) for the 4 tables: `patients`, `risk_scores`, `triage_queue`, `outreach_logs`. Read-only from the UI except outreach approval (inserts into `outreach_logs`).
4. No schema changes — purely binds to your existing tables. If a query returns empty, screens gracefully show empty states (no mock fallback unless you want one).

### Auth — pure simulation

- `/` (login) renders the animated SMART-on-FHIR sequence from `login.html` (particles, orbs, OAuth step list).
- Any button click sets `localStorage.vayu_demo_user` and navigates to `/dashboard`. A lightweight `_authenticated` layout checks that flag and redirects to `/` otherwise. No Supabase Auth.

### Routes

| Path           | Source mockup       | Contents                                                                                                                                                                                            |
| -------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/`            | login.html          | Animated hero, simulated OAuth stepper, "Continue" CTA                                                                                                                                              |
| `/dashboard`   | dashboard.html      | Stat cards, H3 hex map **placeholder** (SVG honeycomb w/ risk coloring), patient queue table from `triage_queue` joined to `patients` + latest `risk_scores`                                        |
| `/patient/$id` | patient-detail.html | Header w/ demographics, 3 Risk Rings (resp/cardio/metabolic) from `risk_scores.probabilities`, XAI horizontal bar chart (Recharts) from `risk_scores` drivers, 72h trajectory line chart, meds list |
| `/outreach`    | outreach.html       | 4-step approval stepper, EN/ES SMS preview cards, "Approve & Send" inserts a row into `outreach_logs`                                                                                               |
| `/analytics`   | analytics.html      | KPI metric cards, ED-visits-prevented line chart, ROI bar chart, cohort breakdown (Recharts)                                                                                                        |
| `/consumer`    | consumer.html       | 393px phone frame with Health-Weather Score, gradient header, daily forecast                                                                                                                        |

### Reusable components (`src/components/vayu/`)

- `TopBar`, `SideNav` (glass, active = teal-dim)
- `RiskRing` (SVG circular progress, animated stroke-dashoffset)
- `PatientCard`, `StatCard`, `NudgeAlert`
- `HexMapPlaceholder` (SVG H3-style honeycomb, hover tooltip)
- `XaiBars` (Recharts horizontal BarChart, red=risk / teal=protective)
- `RiskTrajectoryChart` (Recharts LineChart w/ gradient fill)
- `Stepper` (outreach workflow)
- `PhoneFrame` (consumer wrapper)

### Charts

Recharts (lighter than chartjs, matches React idioms). Custom dark theming via CSS vars.

### Dependencies to add

`@fontsource-variable/inter`, `recharts`, `@supabase/supabase-js`, `lucide-react` (icons already present in shadcn setup likely).

### Out of scope (this iteration)

- Real H3/Mapbox map (placeholder honeycomb only — per your spec)
- Real SMART-on-FHIR OAuth
- Schema migrations (you own the schema)
- Twilio integration (outreach approval only writes a log row)

### Verification

After build: load `/`, click through to `/dashboard`, confirm a patient row navigates to `/patient/:id` and charts render. Empty-state if your tables have no rows yet — let me know if you want me to also generate a SQL seed file you can run yourself.
