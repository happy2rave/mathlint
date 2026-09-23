# v0.11 "App quality" — design

Date: 2026-09-23
Status: approved

## Goal

Make the web page an app you can rely on before it goes to the app stores in
v1.0: installable, working offline, remembering what you solved, fast to start,
readable by a screen reader, and speaking Romanian, Russian and Spanish as well
as English — steps included.

## 1. Translated steps: a message catalog in Python

Every sentence a student reads is written in Python as an English f-string. The
catalog keeps English as the source of truth and translates at the edge.

- `mathlint/i18n.py` defines `_(template, **args)`. It returns a `Message`, a
  `str` subclass holding the English rendering, the template and the arguments.
  Everywhere in Python it *is* the English string, so the command line, the
  tests and `explain.py`'s word matching are unchanged.
- `localize(value, lang)` walks a reply (dicts, lists, strings) and renders every
  `Message` from `mathlint/locales/<lang>.json`, keyed by the English template.
  Arguments that are themselves messages are localized first. A template with no
  translation, or a plain `str`, stays English.
- `web_api.handle` takes an optional `lang` in the payload and localizes the
  result and error messages. `mathlint solve --lang ro` does the same on the
  command line.
- A string that is concatenated or re-formatted loses its template and falls
  back to English; the catalog tests below catch the ones that matter.
- `scripts/extract_messages.py` collects every `_("...")` template with the
  `ast` module and adds new ones to each catalog (value `null` = untranslated).
- Tests: every catalog has every template, no stale templates, the same
  `{placeholders}` as the English, and the problem bank solved in each language
  contains no English step text.

Wrapped: step text in solve, calc and steps; the checker's messages and hints;
the Why? table; practice labels; errors raised to the page.

## 2. Translated interface

- `web/i18n.js` exports `t(key, args)`, `setLanguage(lang)` and `language()`,
  and fills elements carrying `data-i18n`, `data-i18n-aria-label` and
  `data-i18n-placeholder`. Dictionaries live in `web/locales/{en,ro,ru,es}.json`.
- The language defaults to `navigator.language` when supported, is kept in
  `localStorage` as `mathlint:lang`, sets `<html lang>`, and is chosen in the
  About sheet. Every engine request carries `lang`.
- Example labels and group names are translated through the same dictionaries.

## 3. History and favourites

- `web/history.js` keeps entries in `localStorage` (`mathlint:history`):
  `{id, tab, input, kind, answer, time, starred}`. Solve, Check and Work out
  add an entry after a successful run; the same input moves to the top instead
  of repeating.
- A History sheet opens from the top bar: All / Starred, tap to reopen, a star
  to keep, delete one, clear all behind a confirmation. At most 200 unstarred
  entries are kept; starred ones are never dropped.
- Every read and write is wrapped in `try/catch`; without storage the app works
  and the sheet says history is unavailable.

## 4. Installable and offline

- `scripts/build_web.py` vendors everything the page loads from a CDN into
  `_site/vendor/`: the Pyodide runtime with SymPy, mpmath and their lock file,
  KaTeX with its fonts, MathLive, and the Figtree and Spline Sans Mono fonts.
  Downloads are cached in `.cache/vendor/` and checked against pinned SHA-256
  hashes. The page makes no third-party requests.
- `manifest.webmanifest` with PNG icons generated at build time (192, 512 and a
  maskable 512) from the logo, drawn by a small pure-Python rasteriser.
- `sw.js` precaches the page and the engine on install under a cache named by
  the build stamp, serves cache-first, deletes old caches on activate, and does
  not take over until the page asks. A waiting worker shows "A new version is
  ready — Reload". The engine pill says when the device is offline.

## 5. Speed and performance budgets

- The worker fetches the wheel while SymPy loads and unpacks it with
  `pyodide.unpackArchive` instead of loading micropip.
- After the engine is ready it imports the solver modules in the background, so
  the first real request does not pay for them.
- `performance.mark` records page start, engine ready and warm; About shows the
  start-up time.
- `scripts/budget.py`, run in CI after the build: the page's own code under a
  compressed-size budget, a fixed number of requests before first paint, and a
  budget on `import mathlint.web_api`.

## 6. Accessibility

- `web/speech.js` turns the LaTeX mathlint writes into words in the chosen
  language (fractions, powers, roots, functions, relations, derivatives,
  integrals, limits, matrices, intervals). Rendered math is `aria-hidden` and a
  visually hidden spoken text sits beside it, so TalkBack, VoiceOver and NVDA
  read the same words.
- Keypad keys get spoken names; the answer is announced through a live region
  and focus moves to the result heading; graphs and number lines get a text
  description; margin marks are named.
- `node --test web/tests/` covers `speech.js`, `i18n.js` and `history.js`; CI runs
  it. The built page is audited with axe in a browser before release.

## 7. Release

v0.11.0 with the changelog, README, roadmap and web page updated.

## Out of scope

Right-to-left languages, plural rules beyond what full-sentence templates
cover, cloud sync, and native app packaging (v1.0).
