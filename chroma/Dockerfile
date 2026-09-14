# Folyo Chroma — bağımsız vektör DB servisi (Coolify dahil, sıfır ayar).
#
# Dosyaları YALNIZCA bu süreç sahiplenir; web-api / worker / panel-api HTTP ile
# bağlanır (chroma_store → HttpClient). Çok süreçli paylaşımlı dosya erişiminden
# kaynaklanan segment bozulmaları ('finding id') bu mimariyle ortadan kalkar.
#
# Veri: `/data` (kalıcı volume bağla — COPY/silinmez; önceki `chroma_data` dizinini
# buraya mount edersen mevcut veri devralınır).
FROM chromadb/chroma:1.5.9

ENV IS_PERSISTENT=TRUE \
    ANONYMIZED_TELEMETRY=FALSE \
    CHROMA_SERVER_CORS_ALLOW_ORIGINS="*"

VOLUME /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v2/heartbeat', timeout=3)"