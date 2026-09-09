export default function Avatar({ size = "h-8 w-8" }) {
  return (
    <img
      src="/logo.svg"
      alt="Folyo"
      className={`${size} shrink-0 select-none rounded-lg drop-shadow`}
      aria-hidden="true"
    />
  )
}
