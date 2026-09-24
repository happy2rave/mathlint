// The ruled sheet: every line is a MathLive <math-field>, so fractions stack,
// powers rise and integrals look like integrals while you type.
import { t } from "./i18n.js";

const TOUCH = window.matchMedia("(pointer: coarse)").matches;

// Typed shortcuts, on top of MathLive's own (sin, sqrt, pi, / for a fraction...).
// "int" gives a plain integral; MathLive's default adds two empty limit boxes.
const SHORTCUTS = {
  int: String.raw`\int`,
  "d/dx": String.raw`\frac{d}{dx}`,
};

// MathLive's text box lives in the field's shadow root and has no name of its
// own. The field's label goes there: on <math-field> itself, which has no role,
// aria-label and aria-labelledby are not valid ARIA and screen readers skip them.
export function nameField(field, label = null) {
  if (label !== null) field.dataset.label = label;
  for (const attribute of ["aria-label", "aria-labelledby"]) {
    const value = field.getAttribute(attribute);
    if (!value) continue;
    field.dataset[attribute === "aria-label" ? "label" : "labelledby"] = value;
    field.removeAttribute(attribute);
  }
  const labelledBy = field.dataset.labelledby && document.getElementById(field.dataset.labelledby);
  const name = labelledBy ? labelledBy.textContent.trim() : field.dataset.label || "";
  const sink = field.shadowRoot?.querySelector('[part="keyboard-sink"]');
  if (sink && name) sink.setAttribute("aria-label", name);
}

export function configureField(field) {
  nameField(field);
  // the text box may be drawn a moment later; name it before anyone reaches it
  requestAnimationFrame(() => nameField(field));
  field.addEventListener("focusin", () => nameField(field));
  // our keypad replaces MathLive's keyboard
  field.mathVirtualKeyboardPolicy = "manual";
  field.smartFence = true;
  field.inlineShortcuts = { ...field.inlineShortcuts, ...SHORTCUTS };
  if (TOUCH) {
    // keep the phone's own keyboard from covering the math keypad
    field.addEventListener("focusin", () => {
      const sink = field.shadowRoot && field.shadowRoot.querySelector('[part="keyboard-sink"]');
      if (sink) sink.setAttribute("inputmode", "none");
    });
  }
}

const MATRIX_LINE = /^\s*(~|=)?\s*(\[.*\])\s*$/;

// Turn a line written in mathlint's text notation into LaTeX for a math field.
// LaTeX passes through untouched.
export function toLatex(text) {
  const line = text.trim();
  const convert = window.MathLive && window.MathLive.convertAsciiMathToLatex;
  // a backslash or a brace means it is LaTeX already ("x^{2}=x" has no backslash)
  if (!line || /[\\{}]/.test(line) || !convert) return line;

  const matrix = line.match(MATRIX_LINE);
  if (matrix) {
    const prefix = { "~": String.raw`\sim `, "=": "=" }[matrix[1]] || "";
    return prefix + matrixToLatex(matrix[2], convert);
  }

  // MathLive's AsciiMath reader keeps "d/dx" as a slash and glues "[" onto the
  // next letter, so give it the forms it reads correctly.
  const prepared = line
    .replaceAll("[", "(")
    .replaceAll("]", ")")
    .replace(/\bd\/d([A-Za-z])\b/g, "(d)/(d$1)");
  try {
    return convert(prepared);
  } catch {
    return line;
  }
}

// "[[1, 2], [3, 4]]" or "[1 2; 3 4]" -> a pmatrix
function matrixToLatex(body, convert) {
  const inner = body.trim().slice(1, -1).trim();
  const rows = inner.startsWith("[")
    ? inner.split(/\]\s*,\s*\[/).map((row) => row.replace(/[[\]]/g, "").split(","))
    : inner.split(";").map((row) => (row.includes(",") ? row.split(",") : row.trim().split(/\s+/)));
  const cells = rows.map((row) => row.map((cell) => convert(cell.trim())).join("&"));
  return String.raw`\begin{pmatrix}` + cells.join(String.raw`\\`) + String.raw`\end{pmatrix}`;
}

export function setFieldValue(field, text) {
  field.value = toLatex(text);
}

// MathLive writes a few commands KaTeX does not know; show them as KaTeX can.
export function displayLatex(latex) {
  return latex
    .replaceAll(String.raw`\differentialD`, String.raw`\mathrm{d}`)
    .replaceAll(String.raw`\exponentialE`, String.raw`\mathrm{e}`)
    .replaceAll(String.raw`\imaginaryI`, String.raw`\mathrm{i}`)
    .replaceAll(String.raw`\placeholder{}`, String.raw`\square`)
    .replaceAll(String.raw`\mleft`, String.raw`\left`)
    .replaceAll(String.raw`\mright`, String.raw`\right`);
}

export class MathSheet {
  // onEnter: what Enter does in this sheet (by default it starts a new line)
  constructor(list, { onChange, onEnter, lineLabel } = {}) {
    this.list = list;
    this.lineLabel = lineLabel || t("check.line");
    this.onChange = onChange || (() => {});
    this.onEnter = onEnter || ((field) => this.newLineAfter(field));
    this.active = null;
    // capture phase: see Enter and Backspace before MathLive handles them
    window.addEventListener("keydown", (event) => this.#onKeydown(event), true);
  }

  get fields() {
    return [...this.list.querySelectorAll("math-field")];
  }

  // The words a screen reader says for each line, in a new language.
  relabel(lineLabel) {
    this.lineLabel = lineLabel;
    for (const field of this.fields) nameField(field, lineLabel);
    for (const button of this.list.querySelectorAll(".line-remove")) {
      button.setAttribute("aria-label", t("check.removeLine"));
    }
  }

  contains(field) {
    return Boolean(field) && this.list.contains(field);
  }

  setLines(lines) {
    this.list.replaceChildren();
    const content = lines.length ? lines : [""];
    for (const line of content) {
      const field = this.#append(null);
      setFieldValue(field, line);
    }
    this.active = this.fields[0] || null;
    this.#markActive();
  }

  getLines() {
    return this.fields.map((field) => field.value.trim());
  }

  // The lines with something on them, in order: line n of a report is the n-th.
  filledFields() {
    return this.fields.filter((field) => field.value.trim());
  }

  // A teacher's mark on the margin of each line: {verdict} per filled line.
  setMarks(verdicts) {
    this.clearMarks();
    this.filledFields().forEach((field, index) => {
      const verdict = verdicts[index];
      if (!verdict) return;
      const row = field.closest("li");
      row.dataset.mark = verdict.toLowerCase();
      // the margin mark is drawn by CSS; a screen reader gets it in words
      const word = document.createElement("span");
      word.className = "sr-only mark-word";
      word.textContent = t("verdict." + verdict);
      row.append(word);
    });
  }

  clearMarks() {
    for (const row of this.list.children) {
      delete row.dataset.mark;
      row.querySelector(".mark-word")?.remove();
    }
  }

  // What gets checked: the non-empty lines, one per line of text.
  getText() {
    return this.getLines()
      .filter((line) => line)
      .join("\n");
  }

  addLine() {
    return this.newLineAfter(this.fields.at(-1));
  }

  newLineAfter(field) {
    const next = this.#append(field ? field.closest("li") : null);
    next.focus();
    this.onChange();
    return next;
  }

  removeLine(field) {
    if (this.fields.length <= 1) return;
    const fields = this.fields;
    const index = fields.indexOf(field);
    const previous = fields[Math.max(0, index - 1)] === field ? fields[1] : fields[index - 1];
    field.closest("li").remove();
    previous.focus();
    previous.executeCommand("moveToMathfieldEnd");
    this.onChange();
  }

  #append(afterRow) {
    const row = document.createElement("li");
    row.className = "math-line";
    const field = document.createElement("math-field");
    field.setAttribute("aria-label", this.lineLabel);
    // only shown while there is more than one line
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "line-remove";
    remove.setAttribute("aria-label", t("check.removeLine"));
    remove.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-close"/></svg>';
    remove.addEventListener("pointerdown", (event) => event.preventDefault());
    remove.addEventListener("click", () => this.removeLine(field));
    row.append(field, remove);
    if (afterRow) afterRow.after(row);
    else this.list.append(row);
    // a math field can only be configured once it is on the page
    configureField(field);
    field.addEventListener("focusin", () => {
      this.active = field;
      this.#markActive();
    });
    field.addEventListener("input", () => {
      delete row.dataset.mark;
      this.onChange();
    });
    return field;
  }

  #markActive() {
    for (const row of this.list.children) {
      row.classList.toggle("active", row.contains(this.active));
    }
  }

  #onKeydown(event) {
    const field = event.composedPath().find((element) => element.tagName === "MATH-FIELD");
    if (!this.contains(field)) return;

    // Ctrl/Cmd+Enter is left alone: the page uses it to run the check
    if (event.key === "Enter" && !event.shiftKey && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      event.stopImmediatePropagation();
      this.onEnter(field);
      return;
    }
    if (event.key === "Backspace" && field.value === "" && this.fields.length > 1) {
      event.preventDefault();
      event.stopImmediatePropagation();
      this.removeLine(field);
    }
  }
}
