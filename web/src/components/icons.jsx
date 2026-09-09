/* Minimal satır ikon seti (Heroicons Outline benzeri, stroke tabanlı) */

function S({ children, className = "h-5 w-5" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

export const PlusIcon = (p) => (
  <S {...p}>
    <path d="M12 4.5v15m7.5-7.5h-15" />
  </S>
)

export const ArrowUpIcon = (p) => (
  <S {...p}>
    <path d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
  </S>
)

export const SunIcon = (p) => (
  <S {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
  </S>
)

export const MoonIcon = (p) => (
  <S {...p}>
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </S>
)

export const SparkIcon = (p) => (
  <S {...p}>
    <path d="M12 3.5 13.7 9l5.3 1.7-5.3 1.7L12 17.9l-1.7-5.5L5 10.7 10.3 9 12 3.5z" />
  </S>
)

export const DocIcon = (p) => (
  <S {...p}>
    <path d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3.75H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9z" />
  </S>
)

export const ShieldIcon = (p) => (
  <S {...p}>
    <path d="M12 3l7 3v5c0 4.97-3 8.44-7 10-4-1.56-7-5.03-7-10V6l7-3z" />
    <path d="m9 12 2 2 4-4" />
  </S>
)

export const LangIcon = (p) => (
  <S {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18" />
    <path d="M12 3c2.6 2.7 4 5.7 4 9s-1.4 6.3-4 9c-2.6-2.7-4-5.7-4-9s1.4-6.3 4-9z" />
  </S>
)

export const XIcon = (p) => (
  <S {...p}>
    <path d="M6 18 18 6M6 6l12 12" />
  </S>
)

export const MenuIcon = (p) => (
  <S {...p}>
    <path d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
  </S>
)
