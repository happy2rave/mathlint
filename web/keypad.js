// A calculator-style keypad, in the spirit of Photomath's: keys insert real
// structures (a fraction with two boxes, a power, a root, an integral) rather
// than characters, and the cursor lands in the first empty box.

const r = String.raw;

// A key: `label` is LaTeX drawn with KaTeX, or `text` is shown as is.
// It does one of: `insert` (MathLive LaTeX, #0/#? are boxes, #@ grabs what is
// left of the cursor), `command` (a MathLive command) or `action`.
const digit = (d) => ({ label: d, insert: d, kind: "digit" });
const letter = (l) => ({ label: l, insert: l, kind: "letter" });
const LEFT = { text: "←", command: "moveToPreviousChar", kind: "action", title: "Move left" };
const RIGHT = { text: "→", command: "moveToNextChar", kind: "action", title: "Move right" };
const DELETE = { text: "⌫", command: "deleteBackward", kind: "action", title: "Delete" };
const ENTER = { text: "↵", action: "enter", kind: "enter", title: "New line" };
const OPEN = { label: "(", insert: "(", kind: "op" };
const CLOSE = { label: ")", insert: ")", kind: "op" };

export const TABS = [
  {
    id: "basic",
    text: "123",
    columns: 8,
    rows: [
      [digit("7"), digit("8"), digit("9"), { label: r`\div`, insert: r`\div`, kind: "op" },
        { label: r`\frac{\square}{\square}`, insert: r`\frac{#@}{#?}`, title: "Fraction" },
        { label: r`\square^2`, insert: r`#@^{2}`, title: "Square" },
        { label: r`\square^{\square}`, insert: r`#@^{#?}`, title: "Power" },
        { label: r`\sqrt{\square}`, insert: r`\sqrt{#0}`, title: "Square root" }],
      [digit("4"), digit("5"), digit("6"), { label: r`\times`, insert: r`\cdot`, kind: "op" },
        OPEN, CLOSE, letter("x"), { label: r`\pi`, insert: r`\pi` }],
      [digit("1"), digit("2"), digit("3"), { label: "-", insert: "-", kind: "op" },
        { label: "=", insert: "=", kind: "op" }, { label: r`\pm`, insert: r`\pm`, kind: "op" },
        letter("y"), { label: "e", insert: "e", title: "Euler's number" }],
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
        { label: r`e^{\square}`, insert: r`e^{#0}`, title: "e to the power" },
        { label: r`|\square|`, insert: r`\left|#0\right|`, title: "Absolute value" }],
      [{ label: r`\sin^{-1}`, insert: r`\sin^{-1}\left(#0\right)` },
        { label: r`\cos^{-1}`, insert: r`\cos^{-1}\left(#0\right)` },
        { label: r`\tan^{-1}`, insert: r`\tan^{-1}\left(#0\right)` },
        { label: r`\sec`, insert: r`\sec\left(#0\right)` },
        { label: r`\csc`, insert: r`\csc\left(#0\right)` },
        { label: r`\sqrt[n]{\square}`, insert: r`\sqrt[#?]{#0}`, title: "n-th root" },
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
      [{ label: r`\frac{d}{dx}`, insert: r`\frac{d}{dx}\left(#0\right)`, title: "Derivative" },
        { label: r`\frac{d^2}{dx^2}`, insert: r`\frac{d^2}{dx^2}\left(#0\right)`, title: "Second derivative" },
        { label: r`\int\square`, insert: r`\int #0\,dx`, title: "Integral" },
        { label: r`\int_a^b`, insert: r`\int_{#?}^{#?} #0\,dx`, title: "Definite integral" },
        { label: r`dx`, insert: r`\,dx` },
        { label: r`+C`, insert: "+C", title: "Constant of integration" },
        letter("x"), letter("t")],
      [{ label: "=", insert: "=", kind: "op" },
        { label: r`\Rightarrow`, insert: r`\Rightarrow `, title: "Implies (at the start of a line)" },
        { text: "or", insert: r`\text{ or }`, title: "Another solution" },
        { text: "no sol.", insert: r`\text{no solution}`, title: "No solution" },
        { label: r`\pm`, insert: r`\pm`, kind: "op" },
        { label: r`\sim`, insert: r`\sim `, title: "Row-equivalent (row reduction)" },
        { text: "2×2", insert: r`\begin{pmatrix}#0&#?\\#?&#?\end{pmatrix}`, title: "2 by 2 matrix" },
        { text: "3×3", insert: r`\begin{pmatrix}#0&#?&#?\\#?&#?&#?\\#?&#?&#?\end{pmatrix}`, title: "3 by 3 matrix" }],
      [{ label: r`\square^{\square}`, insert: r`#@^{#?}`, title: "Power" },
        { label: r`\frac{\square}{\square}`, insert: r`\frac{#@}{#?}`, title: "Fraction" },
        { label: r`\sqrt{\square}`, insert: r`\sqrt{#0}`, title: "Square root" },
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
  constructor(root, { getTarget, onEnter, onInput }) {
    this.root = root;
    this.getTarget = getTarget;
    this.onEnter = onEnter;
    this.onInput = onInput || (() => {});
    this.tab = TABS[0].id;
    this.render();
  }

  render() {
    this.root.replaceChildren();
    this.root.classList.add("keypad");

    const tabs = document.createElement("div");
    tabs.className = "keypad-tabs";
    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", "Keypad");
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
    this.root.append(tabs);

    const tab = TABS.find((candidate) => candidate.id === this.tab);
    const grid = document.createElement("div");
    grid.className = "keypad-grid";
    grid.style.setProperty("--columns", String(tab.columns));
    for (const row of tab.rows) {
      for (const key of row) grid.append(this.#keyButton(key));
    }
    this.root.append(grid);
  }

  #keyButton(key) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `key key-${key.kind || "math"}`;
    if (key.title) {
      button.title = key.title;
      button.setAttribute("aria-label", key.title);
    }
    if (key.text) {
      button.textContent = key.text;
    } else if (window.katex) {
      // fractions shrink to unreadable in inline style
      const tall = /\\frac/.test(key.label);
      window.katex.render((tall ? r`\displaystyle ` : "") + key.label, button, { throwOnError: false });
      if (!key.title) button.setAttribute("aria-label", key.label.replace(/\\/g, ""));
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
