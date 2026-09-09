import { ArrowLeftIcon, MoonIcon, SunIcon } from "./icons.jsx"

/**
 * Sağ kolonun başlığı (yalnızca içerik alanının üstünde — sidebar'a binmez).
 * Logo sidebar'dadır; burada: geri butonu + sohbet adı + tema değiştirici.
 */
export default function Header({ theme, onToggleTheme, onBack, title }) {
  const dark = theme === "gemdark"
  return (
    <header className="flex h-14 shrink-0 items-center gap-2 px-3 sm:px-4">
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