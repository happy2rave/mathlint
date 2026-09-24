// The page's words in the reader's language. English is the source: a word
// missing from another language falls back to English, then to its key.
//
//   t("solve.button")                        -> "Solve"
//   t("steps.progress", { shown: 2, total: 5 }) -> "Step 2 of 5"
//
// Elements carry their keys: data-i18n (text), data-i18n-html (trusted markup
// from our own dictionaries), data-i18n-aria-label, data-i18n-title and
// data-i18n-placeholder.

export const LANGUAGES = ["en", "ro", "ru", "es"];
export const LANGUAGE_KEY = "mathlint:lang";

let current = "en";
let english = {};
let words = {};
const listeners = new Set();

// The saved choice, else the first of the browser's languages we speak.
export function pickLanguage(saved, preferred = []) {
  if (LANGUAGES.includes(saved)) return saved;
  for (const tag of preferred) {
    const base = String(tag).toLowerCase().split("-")[0];
    if (LANGUAGES.includes(base)) return base;
  }
  return "en";
}

export function language() {
  return current;
}

// For tests and for setLanguage: the dictionaries themselves.
export function useDictionaries(lang, englishWords, languageWords = englishWords) {
  current = lang;
  english = englishWords || {};
  words = languageWords || {};
}

export function t(key, args = {}) {
  const template = words[key] ?? english[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (whole, name) => (name in args ? String(args[name]) : whole));
}

async function load(lang, fetchJson) {
  try {
    return await fetchJson(`locales/${lang}.json`);
  } catch {
    return {};
  }
}

export async function setLanguage(lang, { fetchJson = defaultFetch, save = true } = {}) {
  const chosen = LANGUAGES.includes(lang) ? lang : "en";
  const englishWords = Object.keys(english).length ? english : await load("en", fetchJson);
  const languageWords = chosen === "en" ? englishWords : await load(chosen, fetchJson);
  useDictionaries(chosen, englishWords, languageWords);
  if (save) {
    try {
      localStorage.setItem(LANGUAGE_KEY, chosen);
    } catch {
      /* the choice lasts until the page is closed */
    }
  }
  if (typeof document !== "undefined") {
    document.documentElement.lang = chosen;
    applyTranslations(document);
  }
  for (const listener of listeners) listener(chosen);
}

export function onLanguageChange(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function applyTranslations(root) {
  for (const element of root.querySelectorAll("[data-i18n]")) {
    element.textContent = t(element.dataset.i18n);
  }
  for (const element of root.querySelectorAll("[data-i18n-html]")) {
    element.innerHTML = t(element.dataset.i18nHtml);
  }
  for (const [attribute, name] of [
    ["i18nAriaLabel", "aria-label"],
    ["i18nTitle", "title"],
    ["i18nPlaceholder", "placeholder"],
  ]) {
    const selector = "[data-" + attribute.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase()) + "]";
    for (const element of root.querySelectorAll(selector)) {
      element.setAttribute(name, t(element.dataset[attribute]));
    }
  }
}

async function defaultFetch(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: ${response.status}`);
  return response.json();
}
