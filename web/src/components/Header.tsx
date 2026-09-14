import { ArrowLeftIcon, MenuIcon, MoonIcon, SunIcon } from "./icons"
import type { ThemeValue } from "../enums/index"

interface HeaderProps {
  theme: ThemeValue
  onToggleTheme: () => void
  onBack?: () => void
  onMenu?: () => void
  title: string
  onLogout?: () => void
}

export default function Header({ theme, onToggleTheme, onBack, onMenu, title, onLogout }: HeaderProps) {
  const dark = theme === "gemdark"
  return (
    <header className="flex h-14 shrink-0 items-center gap-2 px-3 sm:px-4">
      {onMenu && (
        <button
          type="button"
          className="btn btn-circle btn-ghost -ml-1 shrink-0 md:hidden"
          onClick={onMenu}
          title="Sohbetler"
          aria-label="Sohbetler menüsü"
        >
          <MenuIcon className="h-5 w-5" />
        </button>
      )}
      {onBack && (
        <button
          type="button"
          className="btn btn-circle btn-ghost -ml-1 shrink-0"
          onClick={onBack}
          title="Ana sayfaya dön"
          aria-label="Geri"
        >
          <ArrowLeftIcon className="h-5 w-5" />
        </button>
      )}
      <span className="min-w-0 flex-1 truncate text-base font-semibold tracking-tight">{title || ""}</span>
      {onLogout && (
        <button
          type="button"
          className="btn btn-ghost btn-sm shrink-0 px-2"
          onClick={onLogout}
          title="Çıkış yap"
        >
          Çıkış Yap
        </button>
      )}
      <button
        type="button"
        className="btn btn-circle btn-ghost shrink-0"
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
    </header>
  )
}