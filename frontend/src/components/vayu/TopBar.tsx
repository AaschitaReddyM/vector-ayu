import { Link, useRouterState } from "@tanstack/react-router";
import { Bell } from "lucide-react";
import { toast } from "sonner";
import { getUser } from "@/lib/auth";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/outreach", label: "Outreach" },
  { to: "/analytics", label: "Analytics" },
  { to: "/consumer", label: "Consumer" },
] as const;

export function TopBar() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const user = getUser();

  return (
    <header className="glass sticky top-0 z-50 h-[62px] px-7 flex items-center justify-between">
      <Link to="/dashboard" className="flex items-center gap-2.5 font-bold text-[1.2rem]">
        <img src="/logo.jpg" alt="Vector-AYU Logo" className="w-8 h-8 object-contain" />
        <span>
          Vector-AY<span className="text-teal">U</span>
        </span>
      </Link>

      <nav className="hidden md:flex gap-1.5">
        {NAV.map((item) => {
          const active =
            path === item.to ||
            (item.to !== "/dashboard" && path.startsWith(item.to)) ||
            (item.to === "/dashboard" && path.startsWith("/patient"));
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`px-4 py-2 rounded-lg text-[0.85rem] font-medium transition-colors ${
                active
                  ? "bg-teal-dim text-teal"
                  : "text-text-dim hover:bg-white/[0.03] hover:text-foreground"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-4">
        <button
          className="relative text-text-dim hover:text-foreground transition-colors"
          onClick={() => toast("No new notifications", { description: "You're all caught up!" })}
        >
          <Bell className="w-[18px] h-[18px]" />
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-coral" />
        </button>
        <div className="w-[34px] h-[34px] rounded-full flex items-center justify-center text-[0.8rem] font-semibold text-[#0a0f1e] bg-gradient-to-br from-teal to-blue">
          {user?.initials ?? "DR"}
        </div>
      </div>
    </header>
  );
}
