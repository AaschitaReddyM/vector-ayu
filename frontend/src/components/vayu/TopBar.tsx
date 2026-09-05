import { useState } from "react";
import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { Bell } from "lucide-react";
import { toast } from "sonner";
import { getUser, signOut } from "@/lib/auth";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/outreach", label: "Outreach" },
  { to: "/analytics", label: "Analytics" },
  { to: "/consumer", label: "Consumer" },
] as const;

export function TopBar() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const user = getUser();

  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="glass sticky top-0 z-50 h-[72px] px-8 flex items-center justify-between">
      <Link to="/dashboard" className="flex items-center gap-3 font-extrabold text-[1.45rem]">
        <img src="/logo.png" alt="Vector-AYU Logo" className="w-10 h-10 object-contain" />
        <span>
          Vector-AY<span className="text-teal">U</span>
        </span>
      </Link>

      <nav className="hidden md:flex gap-2">
        {NAV.map((item) => {
          const active =
            path === item.to ||
            (item.to !== "/dashboard" && path.startsWith(item.to)) ||
            (item.to === "/dashboard" && path.startsWith("/patient"));
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`px-4 py-2.5 rounded-lg text-[1rem] font-semibold transition-colors ${
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

      <div className="flex items-center gap-6">
        {/* Notification Dropdown Container */}
        <div className="relative">
          <button
            className="relative text-text-dim hover:text-foreground transition-colors mt-1"
            onClick={() => setShowNotifications(!showNotifications)}
          >
            <Bell className="w-[22px] h-[22px]" />
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-coral animate-pulse" />
          </button>

          {/* Hardcoded notification for demo purposes */}
          {showNotifications && (
            <div className="absolute top-[120%] right-0 w-[340px] bg-card border border-border rounded-xl shadow-2xl overflow-hidden animate-fade-up z-50">
              <div className="px-4 py-3 border-b border-border font-semibold flex items-center justify-between">
                <span>Pending Approvals</span>
                <span className="text-[0.7rem] bg-coral/20 text-coral px-2 py-0.5 rounded-full font-bold">1 New</span>
              </div>
              <div className="p-2">
                <div 
                  className="p-3 hover:bg-white/5 rounded-lg cursor-pointer transition-colors border-l-2 border-coral"
                  onClick={(e) => {
                    e.currentTarget.style.display = 'none';
                    localStorage.setItem("vayu_consumer_sms", "VAYU Update for James: Air quality near Dallas is Unhealthy (AQI 165). Consider keeping windows closed today. Reply STOP to opt out.");
                    window.dispatchEvent(new Event("vayu_sms_update"));
                    toast.success("SMS & IoT payloads transmitted to James Okonkwo!", { icon: "✅" });
                  }}
                >
                  <div className="text-[0.8rem] font-semibold text-text">Review SMS for James Okonkwo</div>
                  <div className="text-[0.75rem] text-text-dim mt-1">AQI 165 Spike — requires SMS approval and Google Nest payload transmission.</div>
                  <div className="text-[0.7rem] text-teal mt-2 font-semibold">Click to Approve →</div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 border-l border-border pl-6 ml-2">
          <div className="w-[42px] h-[42px] rounded-full flex items-center justify-center text-[0.95rem] font-bold text-[#0a0f1e] bg-gradient-to-br from-teal to-blue shadow-[0_0_15px_rgba(0,212,170,0.3)]">
            {typeof window !== 'undefined' && localStorage.getItem('vayu_region') === 'new_delhi' ? 'RD' : 'AO'}
          </div>
          <button
            onClick={() => {
              signOut();
              navigate({ to: "/" });
            }}
            className="text-[0.85rem] font-bold text-text-dim hover:text-coral hover:bg-coral/10 transition-colors ml-2 px-3 py-1.5 rounded-md"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
