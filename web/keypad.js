// A calculator-style keypad, in the spirit of Photomath's: keys insert real
// structures (a fraction with two boxes, a power, a root, an integral) rather
// than characters, and the cursor lands in the first empty box.
import { t } from "./i18n.js";
import { speak } from "./speech.js";

const r = String.raw;

// A key: `label` is LaTeX drawn with KaTeX, or `text` is shown as is, or
// `textKey` names words in the dictionary; `title` names its spoken name.
// It does one of: `insert` (MathLive LaTeX, #0/#? are boxes, #@ grabs what is
// left of the cursor), `command` (a MathLive command) or `action`.
const digit = (d) => ({ label: d, insert: d, kind: "digit" });
const letter = (l) => ({ label: l, insert: l, kind: "letter" });
const LEFT = { text: "←", command: "moveToPreviousChar", kind: "action", title: "keypad.left" };
const RIGHT = { text: "→", command: "moveToNextChar", kind: "action", title: "keypad.right" };
const DELETE = { text: "⌫", command: "deleteBackward", kind: "action", title: "keypad.delete" };
const ENTER = { text: "↵", action: "enter", kind: "enter", title: "keypad.newLine" };
const OPEN = { label: "(", insert: "(", kind: "op" };
const CLOSE = { label: ")", insert: ")", kind: "op" };

export const TABS = [
  {
    id: "basic",
    text: "123",
    columns: 8,
    rows: [
      [digit("7"), digit("8"), digit("9"), { label: r`\div`, insert: r`\div`, kind: "op" },
        { label: r`\frac{\square}{\square}`, insert: r`\frac{#@}{#?}`, title: "keypad.fraction" },
        { label: r`\square^2`, insert: r`#@^{2}`, title: "keypad.square" },
        { label: r`\square^{\square}`, insert: r`#@^{#?}`, title: "keypad.power" },
        { label: r`\sqrt{\square}`, insert: r`\sqrt{#0}`, title: "keypad.sqrt" }],
      [digit("4"), digit("5"), digit("6"), { label: r`\times`, insert: r`\cdot`, kind: "op" },
        OPEN, CLOSE, letter("x"), { label: r`\pi`, insert: r`\pi` }],
      [digit("1"), digit("2"), digit("3"), { label: "-", insert: "-", kind: "op" },
        { label: "=", insert: "=", kind: "op" }, { label: r`\pm`, insert: r`\pm`, kind: "op" },
        letter("y"), { label: "e", insert: "e", title: "keypad.euler" }],
      [digit("0"), { label: ".", insert: ".", kind: "digit" }, { label: ",", insert: ",", kind: "digit" },
        { label: "+", insert: "+", kind: "op" }, LEFT, RIGHT, DELETE, ENTER],
    ],
  },
  {
    id: "functions",
    text: "f(x)",
    columns: 8,
    rows: [
      [{ label: r`\sin`, insert: r`\sin\left(#0\right)` },
        { label: r`\cos`, insert: r`\cos\left(#0\right)` },
        { label: r`\tan`, insert: r`\tan\left(#0\right)` },
        { label: r`\cot`, insert: r`\cot\left(#0\right)` },
        { label: r`\ln`, insert: r`\ln\left(#0\right)` },
        { label: r`\log`, insert: r`\log\left(#0\right)` },
        { label: r`e^{\square}`, insert: r`e^{#0}`, title: "keypad.exp" },
        { label: r`|\square|`, insert: r`\left|#0\right|`, title: "keypad.abs" }],
      [{ label: r`\sin^{-1}`, insert: r`\sin^{-1}\left(#0\right)` },
        { label: r`\cos^{-1}`, insert: r`\cos^{-1}\left(#0\right)` },
        { label: r`\tan^{-1}`, insert: r`\tan^{-1}\left(#0\right)` },
        { label: r`\sec`, insert: r`\sec\left(#0\right)` },
        { label: r`\csc`, insert: r`\csc\left(#0\right)` },
        { label: r`\sqrt[n]{\square}`, insert: r`\sqrt[#?]{#0}`, title: "keypad.nthRoot" },
        { label: r`\infty`, insert: r`\infty` },
        { label: r`\theta`, insert: r`\theta` }],
      [{ label: r`\sinh`, insert: r`\sinh\left(#0\right)` },
        { label: r`\cosh`, insert: r`\cosh\left(#0\right)` },
        { label: r`\tanh`, insert: r`\tanh\left(#0\right)` },
        letter("a"), letter("b"), letter("n"), letter("t"), letter("x")],
      [OPEN, CLOSE, { label: "=", insert: "=", kind: "op" }, { label: "+", insert: "+", kind: "op" },
        LEFT, RIGHT, DELETE, ENTER],
    ],
  },
  {
    id: "calculus",
    text: r`∫ d/dx`,
    columns: 8,
    rows: [
      [{ label: r`\frac{d}{dx}`, insert: r`\frac{d}{dx}\left(#0\right)`, title: "keypad.derivative" },
        { label: r`\frac{d^2}{dx^2}`, insert: r`\frac{d^2}{dx^2}\left(#0\right)`, title: "keypad.secondDerivative" },
        { label: r`\int\square`, insert: r`\int #0\,dx`, title: "keypad.integral" },
        { label: r`\int_a^b`, insert: r`\int_{#?}^{#?} #0\,dx`, title: "keypad.definite" },
        { label: r`dx`, insert: r`\,dx` },
        { label: r`+C`, insert: "+C", title: "keypad.constant" },
        letter("x"), letter("t")],
      [{ label: "=", insert: "=", kind: "op" },
        { label: r`\Rightarrow`, insert: r`\Rightarrow `, title: "keypad.implies" },
        { textKey: "keypad.orText", insert: r`\text{ or }`, title: "keypad.or" },
        { textKey: "keypad.noSolutionText", insert: r`\text{no solution}`, title: "keypad.noSolution" },
        { label: r`\pm`, insert: r`\pm`, kind: "op" },
        { label: r`\sim`, insert: r`\sim `, title: "keypad.rowEquivalent" },
        { text: "2×2", insert: r`\begin{pmatrix}#0&#?\\#?&#?\end{pmatrix}`, title: "keypad.matrix2" },
        { text: "3×3", insert: r`\begin{pmatrix}#0&#?&#?\\#?&#?&#?\\#?&#?&#?\end{pmatrix}`, title: "keypad.matrix3" }],
      [{ label: r`\lim`, insert: r`\lim_{x\to#0}#?`, title: "keypad.limit" },
        { label: r`\infty`, insert: r`\infty`, title: "keypad.infinity" },
        { label: "<", insert: "<", kind: "op", title: "keypad.less" },
        { label: r`\le`, insert: r`\le `, kind: "op", title: "keypad.lessEqual" },
        { label: ">", insert: ">", kind: "op", title: "keypad.greater" },
        { label: r`\ge`, insert: r`\ge `, kind: "op", title: "keypad.greaterEqual" },
        letter("y"), letter("n")],
      [{ label: r`\square^{\square}`, insert: r`#@^{#?}`, title: "keypad.power" },
        { label: r`\frac{\square}{\square}`, insert: r`\frac{#@}{#?}`, title: "keypad.fraction" },
        { label: r`\sqrt{\square}`, insert: r`\sqrt{#0}`, title: "keypad.sqrt" },
        { label: r`e^{\square}`, insert: r`e^{#0}` },
        { label: r`\ln`, insert: r`\ln\left(#0\right)` },
        { label: r`\sin`, insert: r`\sin\left(#0\right)` },
        { label: r`\cos`, insert: r`\cos\left(#0\right)` },
        { label: r`\pi`, insert: r`\pi` }],
      [OPEN, CLOSE, { label: "+", insert: "+", kind: "op" }, { label: "-", insert: "-", kind: "op" },
        LEFT, RIGHT, DELETE, ENTER],
    ],
  },
  {
    id: "letters",
    text: "abc",
    columns: 10,
    rows: [
      [..."qwertyuiop"].map(letter),
      [..."asdfghjkl"].map(letter).concat([DELETE]),
      [..."zxcvbnm"].map(letter).concat([LEFT, RIGHT, ENTER]),
      [{ label: r`\alpha`, insert: r`\alpha` }, { label: r`\beta`, insert: r`\beta` },
        { label: r`\theta`, insert: r`\theta` }, { label: r`\lambda`, insert: r`\lambda` },
        { label: r`\mu`, insert: r`\mu` }, { label: r`\varphi`, insert: r`\varphi` },
        { label: r`\omega`, insert: r`\omega` }, OPEN, CLOSE, { label: "=", insert: "=", kind: "op" }],
    ],
  },
];

export class Keypad {
  // enterLabel(target): what the Enter key says for that field ("↵", "Solve"...)
  // onDeleteEmpty(target): Delete on an empty line; onHide: the hide key
  constructor(root, { getTarget, onEnter, onInput, enterLabel, onDeleteEmpty, onHide }) {
    this.root = root;
    this.getTarget = getTarget;
    this.onEnter = onEnter;
    this.onInput = onInput || (() => {});
    this.enterLabel = enterLabel || (() => null);
    this.onDeleteEmpty = onDeleteEmpty || (() => false);
    this.onHide = onHide || null;
    this.tab = TABS[0].id;
    this.render();
  }

  // The Enter key's label follows the field it will act on.
  refresh() {
    const target = this.getTarget();
    const label = target ? this.enterLabel(target) : null;
    for (const key of this.root.querySelectorAll(".key-enter")) {
      key.textContent = label || ENTER.text;
      key.classList.toggle("key-enter-word", Boolean(label));
      key.setAttribute("aria-label", label || t(ENTER.title));
    }
  }

  render() {
    this.root.replaceChildren();
    this.root.classList.add("keypad");

    const tabs = document.createElement("div");
    tabs.className = "keypad-tabs";
    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", t("keypad.label"));
    for (const tab of TABS) {
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", String(tab.id === this.tab));
      button.textContent = tab.text;
      keepFocus(button);
      button.addEventListener("click", () => {
        this.tab = tab.id;
        this.render();
      });
      tabs.append(button);
    }
    const bar = document.createElement("div");
    bar.className = "keypad-bar";
    bar.append(tabs);
    if (this.onHide) {
      const hide = document.createElement("button");
      hide.type = "button";
      hide.className = "keypad-hide";
      hide.setAttribute("aria-label", t("keypad.hide"));
      hide.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-chevron-down"/></svg>';
      hide.addEventListener("click", () => this.onHide());
      bar.append(hide);
    }
    this.root.append(bar);

    const tab = TABS.find((candidate) => candidate.id === this.tab);
    const grid = document.createElement("div");
    grid.className = "keypad-grid";
    grid.style.setProperty("--columns", String(tab.columns));
    for (const row of tab.rows) {
      for (const key of row) grid.append(this.#keyButton(key));
    }
    this.root.append(grid);
    this.refresh();
  }

  #keyButton(key) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `key key-${key.kind || "math"}`;
    if (key.title) {
      button.title = t(key.title);
      button.setAttribute("aria-label", t(key.title));
    }
    if (key.textKey) {
      button.textContent = t(key.textKey);
    } else if (key.text) {
      button.textContent = key.text;
    } else if (window.katex) {
      // fractions shrink to unreadable in inline style
      const tall = /\\frac/.test(key.label);
      window.katex.render((tall ? r`\displaystyle ` : "") + key.label, button, { throwOnError: false });
      // a key without a name of its own says its symbol in words: "the square root of"...
      if (!key.title) {
        let words = "";
        try {
          words = speak(key.label, (name, args) => t("speech." + name, args));
        } catch {
          // a key without words is still a key: never lose the whole tab over one
        }
        button.setAttribute("aria-label", words || key.label);
      }
    } else {
      button.textContent = key.label;
    }
    keepFocus(button);
    button.addEventListener("click", () => this.#press(key));
    return button;
  }

  #press(key) {
    const target = this.getTarget();
    if (!target) return;
    if (key.action === "enter") {
      this.onEnter(target);
      return;
    }
    if (key.insert) {
      target.insert(key.insert, { focus: true, selectionMode: "placeholder", scrollIntoView: true });
    } else if (key.command === "deleteBackward" && target.value === "" && this.onDeleteEmpty(target)) {
      return;
    } else if (key.command) {
      target.executeCommand(key.command);
      target.focus();
    }
    this.onInput(target);
  }
}

// Pressing a key must not take the cursor away from the math field.
function keepFocus(button) {
  button.addEventListener("pointerdown", (event) => event.preventDefault());
  button.addEventListener("mousedown", (event) => event.preventDefault());
}
