export const Theme = {
  LIGHT: "gemlight",
  DARK: "gemdark",
} as const

export type ThemeValue = (typeof Theme)[keyof typeof Theme]