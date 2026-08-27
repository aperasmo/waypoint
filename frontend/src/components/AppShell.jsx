import { BookOpen, Compass, Info, Search } from "lucide-react"
import { NavLink, Outlet } from "react-router-dom"

const navigation = [
  {
    to: "/ask",
    label: "Ask",
    icon: Search,
  },
  {
    to: "/browse",
    label: "Browse",
    icon: BookOpen,
  },
  {
    to: "/about",
    label: "About",
    icon: Info,
  },
]

function AppShell() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 bg-waypoint-navy text-white shadow-sm">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <NavLink
            to="/ask"
            className="flex items-center gap-3"
            aria-label="Waypoint home"
          >
            <span className="flex size-9 items-center justify-center rounded-full border border-waypoint-gold/70 text-waypoint-gold">
              <Compass className="size-5" strokeWidth={1.8} />
            </span>

            <span className="text-xl font-semibold tracking-tight">
              Waypoint
            </span>
          </NavLink>

          <nav
            className="hidden items-center gap-1 md:flex"
            aria-label="Primary navigation"
          >
            {navigation.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-white/12 text-white"
                      : "text-white/70 hover:bg-white/8 hover:text-white",
                  ].join(" ")
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <div className="border-b border-waypoint-gold/30 bg-waypoint-gold-soft">
        <div className="mx-auto flex min-h-10 w-full max-w-6xl items-center justify-center gap-2 px-4 text-xs text-slate-700 sm:justify-start sm:px-6 lg:px-8">
          <span
            className="flex size-4 shrink-0 items-center justify-center rounded-full bg-waypoint-gold text-[10px] font-bold text-white"
            aria-hidden="true"
          >
            i
          </span>

          <span>Evidence-based only. Not immigration advice.</span>
        </div>
      </div>

      <main className="mx-auto w-full max-w-6xl px-4 pb-28 pt-8 sm:px-6 md:pb-10 lg:px-8">
        <Outlet />
      </main>

      <nav
        className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 border-t bg-white/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-4px_20px_rgba(0,0,0,0.06)] backdrop-blur md:hidden pb-[env(safe-area-inset-bottom)]"
        aria-label="Primary navigation"
      >
        {navigation.map((item) => {
          const Icon = item.icon

          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  "flex min-h-18 flex-col items-center justify-center gap-1 px-2 text-xs font-medium transition-colors",
                  isActive
                    ? "text-waypoint-blue"
                    : "text-muted-foreground hover:text-foreground",
                ].join(" ")
              }
            >
              <Icon className="size-5" strokeWidth={1.8} />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}

export default AppShell