// The offline app: every file of the site, the math engine included, is kept
// in a cache named for this build. Requests are answered from that cache first,
// so after one visit mathlint works without a connection.
//
// The recognizer (recognizer/: the model, about 4 MB, and its code) is the
// exception: it is kept the first time the camera or the pad asks for it, not
// at install, so a visit that never uses them never downloads it.
//
// scripts/build_web.py fills in VERSION and PRECACHE. A new build installs
// alongside the old one and waits; the page offers "Reload", and only then does
// it take over (see setUpOffline in app.js). Old caches are removed then.

const VERSION = "__VERSION__";
const PRECACHE = __PRECACHE__;
const CACHE = `mathlint-${VERSION}`;

self.addEventListener("install", (event) => {
  // The page's own files are fetched past the browser's HTTP cache, which may
  // still hold the last build's. Vendored files live in folders named for their
  // version, never change, and can come from that cache.
  const requests = PRECACHE.map((url) =>
    url.startsWith("vendor/") ? url : new Request(url, { cache: "reload" })
  );
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(requests)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const name of await caches.keys()) {
        if (name.startsWith("mathlint-") && name !== CACHE) await caches.delete(name);
      }
      // the very first install looks after the page that installed it
      await self.clients.claim();
    })()
  );
});

self.addEventListener("message", (event) => {
  if (event.data === "skip-waiting") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) return;
  event.respondWith(answer(request));
});

async function answer(request) {
  const cache = await caches.open(CACHE);
  // the cache belongs to one build, so "app.js?v=<stamp>" is simply app.js;
  // and any page of the app is the app: "./", "./?x", "./index.html"
  const cached =
    request.mode === "navigate"
      ? await cache.match("./", { ignoreSearch: true })
      : await cache.match(request, { ignoreSearch: true });
  if (cached) return cached;
  if (new URL(request.url).pathname.includes("/recognizer/")) return keep(cache, request);
  try {
    return await fetch(request);
  } catch (error) {
    if (request.mode === "navigate") {
      const page = await cache.match("./", { ignoreSearch: true });
      if (page) return page;
    }
    throw error;
  }
}

// Fetched past the HTTP cache (which may hold the last build's model), then
// kept in this build's cache for offline use.
async function keep(cache, request) {
  const response = await fetch(new Request(request, { cache: "no-cache" }));
  if (response.ok) await cache.put(request, response.clone());
  return response;
}
