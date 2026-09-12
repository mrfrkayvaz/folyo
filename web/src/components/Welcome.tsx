import { type DragEvent, useRef, useState } from "react"
import { DocIcon } from "./icons"

interface WelcomeProps {
  onPickFile: () => void
  onDropFiles: (files: FileList | File[]) => void
}

export default function Welcome({ onPickFile, onDropFiles }: WelcomeProps) {
  const [dragging, setDragging] = useState(false)
  const dragDepth = useRef(0)

  const handleDragEnter = (e: DragEvent<HTMLButtonElement>) => {
    e.preventDefault()
    dragDepth.current += 1
    setDragging(true)
  }
  const handleDragLeave = (e: DragEvent<HTMLButtonElement>) => {
    e.preventDefault()
    dragDepth.current -= 1
    if (dragDepth.current <= 0) {
      dragDepth.current = 0
      setDragging(false)
    }
  }
  const handleDragOver = (e: DragEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "copy"
  }
  const handleDrop = (e: DragEvent<HTMLButtonElement>) => {
    e.preventDefault()
    dragDepth.current = 0
    setDragging(false)
    const files = e.dataTransfer?.files
    if (files?.length) onDropFiles(files)
  }

  return (
    <section className="flex flex-1 flex-col items-center justify-center px-1 py-12 text-center">
      <div className="ctx-rise flex flex-col items-center gap-4">
        <img src="/logo.svg" alt="Folyo" className="h-16 w-16 drop-shadow-lg sm:h-20 sm:w-20" />
        <h1 className="text-4xl font-semibold tracking-tight text-primary sm:text-5xl">Folyo</h1>
        <p className="max-w-xl text-base leading-7 text-base-content/70 sm:text-lg sm:leading-8">
          Bir belge yükleyin (PDF, JPG, PNG, TXT, MD), içeriği hakkında soru sorun.
          Yanıtlar yalnızca belgeden, kaynak göstererek üretilir.
        </p>
      </div>

      <div className="mt-10 w-full max-w-2xl">
        <button
          type="button"
          onClick={onPickFile}
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`group flex w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-3xl border-2 border-dashed px-6 py-14 text-center transition sm:py-16 ${
            dragging
              ? "scale-[1.01] border-primary bg-primary/10"
              : "border-base-300 bg-base-100 hover:border-primary/60 hover:bg-base-200/60"
          }`}
        >
          <span
            className={`flex h-14 w-14 items-center justify-center rounded-2xl transition ${
              dragging
                ? "bg-primary/20 text-primary"
                : "bg-base-200 text-base-content/60 group-hover:bg-primary/10 group-hover:text-primary"
            }`}
          >
            <DocIcon className="h-7 w-7" />
          </span>
          <span className="text-base font-medium text-base-content/80">
            {dragging ? "Bırak ve yükle" : "Belgeyi buraya sürükle"}
          </span>
          <span className="text-sm text-base-content/50">
            veya{" "}
            <span className="font-medium text-primary underline underline-offset-2">
              dosya seçmek için tıkla
            </span>
          </span>
          <span className="mt-1 text-xs text-base-content/40">PDF · JPG · PNG · TXT · MD</span>
        </button>
      </div>
    </section>
  )
}