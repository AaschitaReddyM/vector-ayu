const KEY = "vayu_demo_user";

export type DemoUser = {
  name: string;
  initials: string;
  role: string;
  org: string;
};

const DEFAULT_USER: DemoUser = {
  name: "Dr. Amara Okafor, MD",
  initials: "AO",
  role: "Pulmonology & Internal Medicine",
  org: "Parkland Health — DFW Metro Network",
};

export function signIn(user: Partial<DemoUser> = {}): DemoUser {
  const merged = { ...DEFAULT_USER, ...user };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(KEY, JSON.stringify(merged));
  }
  return merged;
}

export function signOut() {
  if (typeof window !== "undefined") window.localStorage.removeItem(KEY);
}

export function getUser(): DemoUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as DemoUser;
  } catch {
    return null;
  }
}

export function isSignedIn(): boolean {
  return getUser() !== null;
}
