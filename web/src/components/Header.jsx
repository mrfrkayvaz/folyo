import Avatar from "./Avatar.jsx"
import { MenuIcon, MoonIcon, SparkIcon, SunIcon } from "./icons.jsx"

export default function Header({ theme, onToggleTheme, onMenu }) {
  const dark = theme === "gemdark"
  return (
    <header className="navbar h-16 px-2 sm:px-4">
      <div className="navbar-start">
        {onMenu && (
          <button
            type="button"
            className="btn btn-circle btn-ghost md:hidden"
            onClick={onMenu}
            aria-label="Sohbet listesi"
          >
            <MenuIcon className="h-5 w-5" />
          </button>
        )}
        <button type="button" className="btn btn-ghost -ml-2 gap-2 px-2 sm:px-3" tabIndex={-1} aria-hidden="true">
          <Avatar size="h-9 w-9 text-sm" />
          <span className="hidden text-lg font-semibold tracking-tight sm:inline">Contextus</span>
        </button>
      </div>

      <div className="navbar-center hidden md:flex">
        <span className="inline-flex items-center gap-2 rounded-full border border-base-300 bg-base-200/60 px-3.5 py-1.5 text-[13px] text-base-content/75">
          <SparkIcon className="h-4 w-4 text-primary" />
          Belge Analiz &amp; Soru-Cevap
        </span>
      </div>

      <div className="navbar-end">
        <button
          type="button"
          className="btn btn-circle btn-ghost"
          onClick={onToggleTheme}
          title={dark ? "Aydınlık temaya geç" : "Karanlık temaya geç"}
          aria-label="Tema değiştir"
        >
          {dark ? (
            <SunIcon key="sun" className="h-5 w-5 ctx-rise" />
          ) : (
            <MoonIcon key="moon" className="h-5 w-5 ctx-rise" />
          )}
        </button>
      </div>
    </header>
  )
}
