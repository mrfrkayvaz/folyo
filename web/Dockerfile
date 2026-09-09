# --- Build aşaması: Vite prod build ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Statik dağıtım aşaması ---
# nginx kaldırıldı: sunucu rolünü ana dizindeki Caddy (caddy servisi) üstlendi.
# Bu imaj dist'i her başlangıçta paylaşılan `web-static` volume'üne kopyalar ve çıkar (tek seferlik).
FROM alpine:3.20
COPY --from=build /app/dist /srv-dist
CMD ["sh", "-c", "cp -a /srv-dist/. /srv/ && echo 'dist copied to /srv (web-static volume)'; ls /srv | head"]
