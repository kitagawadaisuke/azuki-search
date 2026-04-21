// Eテレさがすくん Service Worker
// 戦略:
//   - 静的アセット（HTML/CSS/JS/icons）: Cache First（オフライン対応）
//   - data.json: Network First → fallback to cache（鮮度優先、オフライン時は古くてもOK）

const CACHE_VERSION = "v2";
const STATIC_CACHE = `etere-static-${CACHE_VERSION}`;
const DATA_CACHE   = `etere-data-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== STATIC_CACHE && k !== DATA_CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // data.json: Network First
  if (url.pathname.endsWith("/data.json")) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(DATA_CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // 静的アセット: Cache First
  event.respondWith(
    caches.match(req).then((cached) => cached || fetch(req).then((res) => {
      // 同一オリジンのGETレスポンスのみキャッシュ
      if (res && res.status === 200 && url.origin === location.origin) {
        const copy = res.clone();
        caches.open(STATIC_CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }))
  );
});
