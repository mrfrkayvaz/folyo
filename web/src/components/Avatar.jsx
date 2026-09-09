export default function Avatar({ size = "h-9 w-9 text-base" }) {
  return (
    <div
      className={`flex ${size} shrink-0 select-none items-center justify-center rounded-full bg-gradient-to-br from-primary via-secondary to-accent font-bold text-white shadow-sm`}
      aria-hidden="true"
    >
      <span className="-mt-0.5">✦</span>
    </div>
  )
}
