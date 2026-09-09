import { renderToStaticMarkup } from "react-dom/server"
import MessageList from "./src/components/MessageList.jsx"
import Composer from "./src/components/Composer.jsx"
import RichText from "./src/components/RichText.jsx"

const md = [
  "**sözleşme.pdf** belgenizden özet:\n\n### Ana yükümlülükler\n- Taraf A, 30 gün içinde **teslim** eder\n- Ödeme, `euro` üzerinden yapılır\n1. Fatura kesilir\n2. 15 gün içinde ödenir\n\n```js\nconst deadline = days(30)\n```\n\n> Gerçek `/api/qa` bağlantısı burada olacak."
]

const messages = [
  { id: "u1", role: "user", text: "Bu sözleşmenin ana yükümlülükleri neler?", file: { name: "sozlesme.pdf", size: 241172 } },
  { id: "a1", role: "assistant", text: md[0], sources: [{ label: "sozlesme.pdf", meta: "s.3 · madde 4" }] },
]

try {
  const out =
    renderToStaticMarkup(<MessageList messages={messages} pending={true} />) +
    renderToStaticMarkup(<RichText text={md[0]} />) +
    renderToStaticMarkup(<Composer file={null} onClearFile={() => {}} onPickFile={() => {}} onSend={() => {}} busy={false} />)
  const checks = {
    "kullanici mesaji var": out.includes("ana yükümlülükleri"),
    "dosya cipi var": out.includes("sozlesme.pdf"),
    "kaynak cipi var": out.includes("madde 4"),
    "guard notu var": out.includes("yalnızca belge kaynaklı"),
    "kod blogu (code/pre) var": out.includes("const deadline"),
    "kalın (<strong>) var": out.includes("<strong>"),
    "liste (<ul>/<ol>) var": out.includes("<ul") && out.includes("<ol"),
    "typing (loading) var": out.includes("loading-dots"),
    "composer textarea var": out.includes("<textarea"),
  }
  for (const [k, v] of Object.entries(checks)) console.log((v ? "[OK]  " : "[YOK] ") + k)
  console.log("toplam cikti:", out.length, "karakter — hata yok")
} catch (err) {
  console.log("RENDER HATASI:", err.message)
  process.exit(1)
}
