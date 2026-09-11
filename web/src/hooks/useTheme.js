import { useEffect, useState } from "react"
import { THEME_KEY } from "../constants/index.js"
import { Theme } from "../enums/index.js"

function initialTheme() {
  try {
    const q = new URLSearchParams(location.search).get("theme")
    return q || localStorage.getItem(THEME_KEY) || Theme.LIGHT
  } catch {
    return Theme.LIGHT
  }
}

export function useTheme() {
  const [theme, setTheme] = useState(initialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {}
  }, [theme])

  const toggle = () => setTheme((t) => (t === Theme.DARK ? Theme.LIGHT : Theme.DARK))
  return { theme, toggle }
}