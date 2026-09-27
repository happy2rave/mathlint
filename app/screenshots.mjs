// Store screenshots of the real page, in every language, at the sizes Google
// Play and the App Store ask for, plus Play's icon and feature graphic.
//
//   uv run python scripts/build_app.py --no-sync   # or build_web.py: the site
//   cd app && npx playwright install chromium       # once
//   npm run screenshots
//
// They are written where fastlane's `supply` and `deliver` look for them
// (fastlane/metadata/android/<locale>/images/ and fastlane/screenshots/<locale>/)
// and kept out of git: they are made again whenever the page changes.

import { createServer } from "node:http";
import { copyFile, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const HERE = dirname(fileURLToPath(import.meta.url));
const SITE = join(HERE, "..", "_site");
const META = join(HERE, "fastlane", "metadata", "android");
const APPLE = join(HERE, "fastlane", "screenshots");

// each language, and the store folders that show it
const LANGUAGES = {
  en: { play: ["en-US"], apple: ["en-US"] },
  ro: { play: ["ro"], apple: ["ro"] },
  ru: { play: ["ru-RU"], apple: ["ru"] },
  es: { play: ["es-ES", "es-419"], apple: ["es-ES", "es-MX"] },
};

// what each store asks for: 6.9" iPhone, 13" iPad, a phone and a 10" tablet
const DEVICES = [
  { store: "apple", folder: "", width: 440, height: 956, scale: 3, prefix: "iphone" },
  { store: "apple", folder: "", width: 1032, height: 1376, scale: 2, prefix: "ipad" },
  { store: "play", folder: "phoneScreenshots", width: 360, height: 720, scale: 3 },
  { store: "play", folder: "tenInchScreenshots", width: 800, height: 1280, scale: 2 },
];

// the scenes, each an example the page already has (web/*examples.json)
const SCENES = [
  { name: "solve", tab: "solve", example: "x^2-5x+6=0" },
  { name: "check", tab: "check", example: String.raw`\frac{d}{dx}\left(x^2\sin x\right)` },
  { name: "calculus", tab: "solve", example: String.raw`\int\frac{3x+5}{\left(x+1\right)\left(x+2\right)}\,dx` },
  { name: "inequality", tab: "solve", example: String.raw`x^2-x-6\ge0` },
  { name: "dark", tab: "solve", example: "3x+2y=16", theme: "dark" },
];

const TYPES = {
  ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".wasm": "application/wasm", ".png": "image/png",
  ".woff2": "font/woff2", ".webmanifest": "application/manifest+json",
};

function serve() {
  const server = createServer(async (request, response) => {
    const path = normalize(decodeURIComponent(new URL(request.url, "http://x").pathname));
    const file = join(SITE, path.endsWith("/") ? path + "index.html" : path);
    try {
      const body = await readFile(file);
      response.writeHead(200, { "content-type": TYPES[extname(file)] || "application/octet-stream" });
      response.end(body);
    } catch {
      response.writeHead(404).end();
    }
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server)));
}

async function shoot(browser, base, device, lang) {
  const context = await browser.newContext({
    viewport: { width: device.width, height: device.height },
    deviceScaleFactor: device.scale,
    isMobile: device.width < 900,
    hasTouch: true,
    locale: lang,
    reducedMotion: "reduce",
    serviceWorkers: "block",
  });
  const page = await context.newPage();
  await page.addInitScript((lang) => localStorage.setItem("mathlint:lang", lang), lang);
  await page.goto(base);
  await page.waitForFunction(() => document.getElementById("engine-pill").dataset.state === "ready", null, {
    timeout: 180000,
  });
  const shots = [];
  for (const [index, scene] of SCENES.entries()) {
    await page.evaluate((theme) => {
      if (theme) document.documentElement.dataset.theme = theme;
      else delete document.documentElement.dataset.theme;
    }, scene.theme ?? null);
    // the page's own buttons, pressed from script: a graph may lie over them
    await page.evaluate((tab) => {
      window.scrollTo({ top: 0, behavior: "instant" });
      document.getElementById(`tab-${tab}`).click();
      document.getElementById(`open-${tab}-examples`).click();
    }, scene.tab);
    await page.evaluate((line) => {
      const rows = [...document.querySelectorAll("#example-list .example-line")];
      rows.find((row) => row.dataset.plain === line).closest(".example").click();
    }, scene.example);
    // the answer (or the marks), then a moment for the fonts and the graph
    const results = scene.tab === "solve" ? "#solved" : "#results";
    await page.waitForFunction((selector) => document.querySelector(selector).childElementCount > 0, results);
    await page.evaluate(() => document.activeElement?.blur?.());
    // the page scrolls smoothly to the answer; once it has, back to the top
    await page.waitForTimeout(1500);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.waitForTimeout(300);
    shots.push({ name: `${index + 1}_${scene.name}.png`, data: await page.screenshot() });
  }
  await context.close();
  return shots;
}

// Play's 1024 x 500 banner: the logo, the name and the page's own first sentence.
async function featureGraphic(browser, base, lang) {
  const page = await browser.newPage({ viewport: { width: 1024, height: 500 } });
  await page.addInitScript((lang) => localStorage.setItem("mathlint:lang", lang), lang);
  await page.goto(base);
  await page.waitForFunction(() => !document.documentElement.classList.contains("translating"));
  const lead = await page.evaluate(() => document.querySelector("[data-i18n='about.lead']").textContent.trim());
  await page.setContent(`<!DOCTYPE html><html lang="${lang}"><head><link rel="stylesheet" href="${base}fonts.css"></head>
    <body style="margin:0;width:1024px;height:500px;display:flex;align-items:center;gap:48px;padding:0 72px;box-sizing:border-box;
      background:#fffdf7 repeating-linear-gradient(transparent 0 51px,#dfe6f5 51px 52px);font-family:Figtree,sans-serif;color:#1d2230">
      <div style="position:absolute;left:40px;top:0;bottom:0;border-left:2px solid #eaa59c"></div>
      <img src="${base}icons/icon-512.png" width="200" height="200" alt="">
      <div><div style="font-size:76px;font-weight:800;letter-spacing:-1px">mathlint</div>
      <div style="font-size:30px;line-height:1.35;max-width:620px">${lead}</div></div></body></html>`);
  await page.waitForTimeout(500);
  const data = await page.screenshot();
  await page.close();
  return data;
}

async function write(path, data) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, data);
}

const server = await serve();
const base = `http://127.0.0.1:${server.address().port}/`;
const browser = await chromium.launch();
try {
  await rm(APPLE, { recursive: true, force: true });
  for (const [lang, stores] of Object.entries(LANGUAGES)) {
    for (const device of DEVICES) {
      const shots = await shoot(browser, base, device, lang);
      for (const locale of stores[device.store]) {
        for (const shot of shots) {
          const path =
            device.store === "apple"
              ? join(APPLE, locale, `${device.prefix}_${shot.name}`)
              : join(META, locale, "images", device.folder, shot.name);
          await write(path, shot.data);
        }
      }
      console.log(`${lang}: ${device.store} ${device.width}x${device.height}@${device.scale}`);
    }
    const banner = await featureGraphic(browser, base, lang);
    for (const locale of stores.play) {
      await write(join(META, locale, "images", "featureGraphic.png"), banner);
      await copyFile(join(SITE, "icons", "icon-maskable-512.png"), join(META, locale, "images", "icon.png"));
    }
  }
} finally {
  await browser.close();
  server.close();
}
