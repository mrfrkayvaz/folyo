# Folyo ARQ Worker — bağımsız servis

Belge işleme görevlerini tüketir: `embed_document` (extract → chunk → embed → Chroma),
`enrich_document` (özet + starter sorular), `workspace_summary`.

- **Kod:** `worker_app/` (worker_settings, worker_runners, services/jobs, ingest/extract/ocr/vision/summary)
- **İzolasyon:** worker, web-api'den **hiçbir şey import etmez** — ihtiyaç duyduğu
  tanımlar (config, models, core, ai/llm, chroma_store, embeddings, bm25, jobs sınırları)
  `worker_app/` içinde **yerel kopyadır**. Servisler arası tek sözleşme Redis kuyruğudur
  (görev adları + `id`'ler) + paylaşılan Postgres/Chroma/storage.
- **Çalıştırma:** `uv run --no-sync arq worker_app.worker_settings.settings`
- **Image:** `worker/Dockerfile` (build context = repo kökü; tesseract + bağımlılıklar)
- **Not:** Yerel kopyalar nedeniyle tanım değişiklikleri web-api ve worker'da eşzamanlı
  güncellenmelidir (drift riski; hâlâ ortak şema panel-api'dedir).