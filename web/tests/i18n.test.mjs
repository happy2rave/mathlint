import { test } from "node:test";
import assert from "node:assert/strict";

import { pickLanguage, setLanguage, t, useDictionaries, language } from "../i18n.js";

const EN = { "solve.button": "Solve", "steps.progress": "Step {shown} of {total}", "only.en": "Only" };
const RO = { "solve.button": "Rezolvă", "steps.progress": "Pasul {shown} din {total}" };

test("words come from the chosen language", () => {
  useDictionaries("ro", EN, RO);
  assert.equal(t("solve.button"), "Rezolvă");
  assert.equal(t("steps.progress", { shown: 2, total: 5 }), "Pasul 2 din 5");
});

test("a missing word falls back to English, then to its key", () => {
  useDictionaries("ro", EN, RO);
  assert.equal(t("only.en"), "Only");
  assert.equal(t("no.such.key"), "no.such.key");
});

test("a placeholder without a value stays visible", () => {
  useDictionaries("en", EN);
  assert.equal(t("steps.progress", { shown: 1 }), "Step 1 of {total}");
});

test("the saved choice wins, then the browser's languages", () => {
  assert.equal(pickLanguage("ru", ["es-ES"]), "ru");
  assert.equal(pickLanguage(null, ["de-DE", "es-MX", "en"]), "es");
  assert.equal(pickLanguage("xx", ["ro"]), "ro");
  assert.equal(pickLanguage(null, ["de"]), "en");
});

test("setLanguage loads English and the language, and survives a missing file", async () => {
  useDictionaries("en", {}, {});
  const files = { "locales/en.json": EN, "locales/es.json": { "solve.button": "Resolver" } };
  const fetchJson = async (url) => {
    if (!(url in files)) throw new Error("404");
    return files[url];
  };
  await setLanguage("es", { fetchJson, save: false });
  assert.equal(language(), "es");
  assert.equal(t("solve.button"), "Resolver");
  assert.equal(t("only.en"), "Only");
  await setLanguage("zz", { fetchJson, save: false });
  assert.equal(language(), "en");
});
