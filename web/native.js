// Inside the Android and iOS apps the page is this same page, run by Capacitor.
// This is the only module that knows: it says which app it is in, and reaches
// the app's plugins (the back button, the system bars). On the web there is no
// Capacitor object, and every function here does nothing.
//
// The page has no build step, so it does not load Capacitor's JavaScript; the
// app's bridge puts each installed plugin on window.Capacitor.Plugins itself.

export function nativePlatform(win = globalThis) {
  const bridge = win.Capacitor;
  if (!bridge?.isNativePlatform?.()) return null;
  const platform = bridge.getPlatform?.();
  return platform === "android" || platform === "ios" ? platform : null;
}

// A plugin the app was built with, or null (on the web, or not installed).
export function plugin(name, win = globalThis) {
  if (!nativePlatform(win)) return null;
  return win.Capacitor.Plugins?.[name] ?? null;
}

// What Android's back button does next, in the order any app answers it: close
// what is open on top, then put the keypad away, then go back to the first tab,
// and only then leave.
export function backStep({ dialog = false, keypadOpen = false, tab = "solve" } = {}) {
  if (dialog) return "dialog";
  if (keypadOpen) return "keypad";
  if (tab !== "solve") return "tab";
  return "leave";
}

// The status bar's icons: dark on the light theme, light on the dark one, and
// the system's own choice while the theme follows the system.
export function barStyle(theme) {
  if (theme === "light") return "LIGHT";
  if (theme === "dark") return "DARK";
  return "DEFAULT";
}

export function followTheme(theme, win = globalThis) {
  const bars = plugin("SystemBars", win);
  if (!bars?.setStyle) return;
  Promise.resolve(bars.setStyle({ style: barStyle(theme) })).catch(() => {});
}

// Calls `onBack` for Android's back button (iOS has none). The button no longer
// leaves the app by itself once something listens to it: `leave` does that.
export function onBackButton(onBack, win = globalThis) {
  plugin("App", win)?.addListener?.("backButton", onBack);
}

export function leave(win = globalThis) {
  const app = plugin("App", win);
  if (app?.minimizeApp) Promise.resolve(app.minimizeApp()).catch(() => {});
}
