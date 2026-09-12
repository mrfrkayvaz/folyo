interface UploadingStateProps {
  statusText?: string
}

export default function UploadingState({ statusText }: UploadingStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
        <span className="loading loading-spinner loading-lg text-primary" />
      </div>
      <p className="max-w-md text-sm leading-6 text-base-content/70">{statusText}</p>
      <p className="text-xs text-base-content/40">
        Bu sırada başka dosyaları da sürükleyip bırakabilirsin — listeye eklenir.
      </p>
    </div>
  )
}