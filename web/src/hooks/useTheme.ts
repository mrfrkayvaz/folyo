import { useEffect, useState } from "react"
import { THEME_KEY } from "../constants/index"
import { Theme } from "../enums/index"
import type { ThemeValue } from "../enums/index"

function initialTheme(): ThemeValue {
  try {
    const q = new URLSearchParams(location.search).get("theme")
    return (q as ThemeValue) || (localStorage.getItem(THEME_KEY) as ThemeValue) || Theme.LIGHT
  } catch {
    return Theme.LIGHT
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<ThemeValue>(initialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {
      /* yerel depo kapalıysa tema yine de çalışır */
    }
  }, [theme])

  const toggle = () => setTheme((t) => (t === Theme.DARK ? Theme.LIGHT : Theme.DARK))
  return { theme, toggle }
}