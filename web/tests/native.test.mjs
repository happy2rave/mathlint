import { test } from "node:test";
import assert from "node:assert/strict";

import { backStep, barStyle, followTheme, leave, nativePlatform, onBackButton, plugin } from "../native.js";

// What Capacitor's bridge puts on the page inside an app.
function app(platform, plugins = {}) {
  return {
    Capacitor: {
      isNativePlatform: () => true,
      getPlatform: () => platform,
      Plugins: plugins,
    },
  };
}

test("on the web there is no app, and nothing happens", () => {
  const web = {};
  assert.equal(nativePlatform(web), null);
  assert.equal(plugin("App", web), null);
  followTheme("dark", web);
  onBackButton(() => {}, web);
  leave(web);
});

test("Capacitor's own web fallback is not an app", () => {
  const win = { Capacitor: { isNativePlatform: () => false, getPlatform: () => "web", Plugins: {} } };
  assert.equal(nativePlatform(win), null);
});

test("the app says which platform it is", () => {
  assert.equal(nativePlatform(app("android")), "android");
  assert.equal(nativePlatform(app("ios")), "ios");
  assert.equal(nativePlatform(app("electron")), null);
});

test("a plugin the app was not built with is simply missing", () => {
  const win = app("ios");
  assert.equal(plugin("App", win), null);
  followTheme("dark", win);
  onBackButton(() => {}, win);
  leave(win);
});

test("the back button reaches the App plugin, and leaving minimizes the app", async () => {
  const calls = [];
  const win = app("android", {
    App: {
      addListener: (event, callback) => calls.push(["listen", event, typeof callback]),
      minimizeApp: async () => calls.push(["minimize"]),
    },
  });
  onBackButton(() => {}, win);
  leave(win);
  await Promise.resolve();
  assert.deepEqual(calls, [["listen", "backButton", "function"], ["minimize"]]);
});

test("the back button closes what is on top first, and leaves last", () => {
  assert.equal(backStep({ dialog: true, keypadOpen: true, tab: "check" }), "dialog");
  assert.equal(backStep({ keypadOpen: true, tab: "check" }), "keypad");
  assert.equal(backStep({ tab: "check" }), "tab");
  assert.equal(backStep({ tab: "linalg" }), "tab");
  assert.equal(backStep({ tab: "solve" }), "leave");
  assert.equal(backStep(), "leave");
});

test("the status bar follows the theme", async () => {
  assert.equal(barStyle("light"), "LIGHT");
  assert.equal(barStyle("dark"), "DARK");
  assert.equal(barStyle("system"), "DEFAULT");
  const styles = [];
  const win = app("ios", { SystemBars: { setStyle: async (options) => styles.push(options.style) } });
  followTheme("dark", win);
  followTheme("system", win);
  assert.deepEqual(styles, ["DARK", "DEFAULT"]);
});

test("a plugin that fails does not break the page", async () => {
  const win = app("android", {
    SystemBars: { setStyle: () => Promise.reject(new Error("no window")) },
    App: { minimizeApp: () => Promise.reject(new Error("gone")) },
  });
  followTheme("light", win);
  leave(win);
  await new Promise((resolve) => setTimeout(resolve, 0));
});
