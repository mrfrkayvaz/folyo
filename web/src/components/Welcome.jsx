import Avatar from "./Avatar.jsx"
import { DocIcon, LangIcon, PlusIcon, ShieldIcon } from "./icons.jsx"

const TILES = [
  { key: "upload", kind: "file", icon: PlusIcon, title: "Belge yükle", desc: "PDF · JPG · PNG — dosya seç" },
  {
    key: "how",
    kind: "prompt",
    icon: DocIcon,
    title: "Nasıl çalışıyor?",
    desc: "OCR, dizinleme ve kaynak gösterimi",
    prompt: "Bu uygulama nasıl çalışıyor? Kısaca anlatır mısın?",
  },
  {
    key: "lang",
    kind: "prompt",
    icon: LangIcon,
    title: "Hangi diller?",
    desc: "Türkçe ve İngilizce belgeler",
    prompt: "Hangi dillerdeki belgeleri işleyebiliyorsunuz?",
  },
  {
    key: "trust",
    kind: "prompt",
    icon: ShieldIcon,
    title: "Doğruluk garantisi",
    desc: "Belgede olmayan bilgi üretilmez",
    prompt: "Yanıtların belge dışına çıkmamasını nasıl sağlıyorsunuz?",
  },
]

export default function Welcome({ onPickFile, onSuggestion }) {
  return (
    <section className="flex flex-1 flex-col items-center justify-center px-1 py-12 text-center">
      <div className="ctx-rise flex flex-col items-center gap-4">
        <Avatar size="h-14 w-14 text-xl" />
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          <span className="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
            Contextus
          </span>
        </h1>
        <p className="max-w-xl text-base leading-7 text-base-content/70 sm:text-lg sm:leading-8">
          Bir belge yükleyin (PDF, JPG, PNG), içeriği hakkında soru sorun.
          Yanıtlar yalnızca belgeden, kaynak göstererek üretilir.
        </p>
      </div>

      <div className="mt-10 grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-2">
        {TILES.map((t) => {
          const Icon = t.icon
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => (t.kind === "file" ? onPickFile() : onSuggestion(t.prompt))}
              className={`group flex items-center gap-3 rounded-2xl border p-4 text-left transition ${
                t.kind === "file"
                  ? "border-primary/30 bg-primary/5 hover:border-primary/50 hover:bg-primary/10"
                  : "border-base-300 bg-base-100 hover:border-base-content/25 hover:bg-base-200"
              }`}
            >
              <span
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                  t.kind === "file" ? "bg-primary/15 text-primary" : "bg-base-200 text-base-content/70 group-hover:bg-base-300"
                }`}
              >
                <Icon className="h-5 w-5" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium">{t.title}</span>
                <span className="block text-xs leading-5 text-base-content/50">{t.desc}</span>
              </span>
            </button>
          )
        })}
      </div>

      <p className="mt-10 max-w-md text-xs leading-5 text-base-content/40">
        Türkçe / İngilizce OCR · semantik arama · hallucination guard
      </p>
    </section>
  )
}
