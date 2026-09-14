import { NavLink } from "react-router-dom"
import type { ReactNode } from "react"

interface NavItem {
  /** Rota — kök (sohbetler/anasayfa) ve /logs gibi alt görünümler. */
  to: string
  label: string
  icon: ReactNode
}

function SohbetlerIcon() {
  return (
    <svg className="size-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.7} aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
      />
    </svg>
  )
}

function LoglarIcon() {
  return (
    <svg className="size-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.7} aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z"
      />
    </svg>
  )
}

/**
 * İkon rayları: en solda yalnızca ikon + tooltip. Rotayla çalışır —
 * aktif görünüm URL'den gelir (NavLink). Yeni görünüm = NAV_ITEMS'e satır.
 */
const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Sohbetler", icon: <SohbetlerIcon /> },
  { to: "/logs", label: "Loglar", icon: <LoglarIcon /> },
]

export default function IconRail() {
  return (
    <nav className="flex w-16 shrink-0 flex-col items-center gap-2 border-r border-base-300/40 py-3">
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          title={item.label}
          aria-label={item.label}
          className={({ isActive }) =>
            `flex size-11 items-center justify-center rounded-xl transition ${
              isActive
                ? "bg-base-200 text-primary shadow-inner ring-1 ring-base-300"
                : "text-base-content/50 hover:bg-base-200/60 hover:text-base-content"
            }`
          }
        >
          {item.icon}
        </NavLink>
      ))}
    </nav>
  )
}