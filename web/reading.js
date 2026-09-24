// What the camera and the pad share: the recognizer, fetched the first time
// either opens (about 4 MB, then offline), and the words for the symbols it
// was unsure of.
import { t } from "./i18n.js";

let loading = null;
let listener = null;

// The recognizer, loaded once: { reader, choose }. ``onProgress(fraction)``
// hears the download (fraction null when its size is unknown).
export function recognizer(onProgress = null) {
  listener = onProgress;
  loading ??= import("./recognizer/index.js")
    .then(async ({ Reader, choose }) => {
      const reader = new Reader();
      await reader.load((loaded, total) => listener?.(total ? loaded / total : null));
      return { reader, choose };
    })
    .catch((error) => {
      loading = null; // offline the first time: try again when asked again
      throw error;
    });
  return loading;
}

// How a token is shown to the student, or null for structure (braces, scripts).
const SHOWN = {
  "-": "−",
  "'": "′",
  [String.raw`\prime`]: "′",
  [String.raw`\cdot`]: "·",
  [String.raw`\times`]: "×",
  [String.raw`\div`]: "÷",
  [String.raw`\pm`]: "±",
  [String.raw`\le`]: "≤",
  [String.raw`\ge`]: "≥",
  [String.raw`\ne`]: "≠",
  [String.raw`\to`]: "→",
  [String.raw`\Rightarrow`]: "⇒",
  [String.raw`\sim`]: "~",
  [String.raw`\infty`]: "∞",
  [String.raw`\pi`]: "π",
  [String.raw`\theta`]: "θ",
  [String.raw`\alpha`]: "α",
  [String.raw`\beta`]: "β",
  [String.raw`\lambda`]: "λ",
  [String.raw`\mu`]: "μ",
  [String.raw`\varphi`]: "φ",
  [String.raw`\Delta`]: "Δ",
  [String.raw`\int`]: "∫",
  [String.raw`\sqrt`]: "√",
  [String.raw`\left(`]: "(",
  [String.raw`\right)`]: ")",
  [String.raw`\left[`]: "[",
  [String.raw`\right]`]: "]",
  [String.raw`\left|`]: "|",
  [String.raw`\right|`]: "|",
  [String.raw`\text{ or }`]: "or",
};
const SILENT = new Set(["{", "}", "^", "_", "&", "\\\\", String.raw`\,`, String.raw`\frac`,
  String.raw`\begin{pmatrix}`, String.raw`\end{pmatrix}`]);

export function symbolName(token) {
  if (SILENT.has(token)) return null;
  if (token in SHOWN) return SHOWN[token];
  if (/^\\[A-Za-z]+$/.test(token)) return token.slice(1); // sin, ln, lim
  return token;
}

// "the 5 on line 2, the x on line 3": what to look at, or "" when nothing.
// ``lines``: what choose() gave for each line, in the notebook's order.
export function unsureText(lines, firstLine = 1) {
  const seen = new Set();
  const items = [];
  lines.forEach((line, index) => {
    for (const { token } of line?.unsure ?? []) {
      const symbol = symbolName(token);
      const key = `${symbol} ${index}`;
      if (!symbol || seen.has(key)) continue;
      seen.add(key);
      items.push(t("read.unsureItem", { symbol, line: index + firstLine }));
    }
  });
  return items.join(", ");
}
