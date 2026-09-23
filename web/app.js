import { MathSheet, configureField, displayLatex, nameField, toLatex } from "./editor.js";
import { Engine } from "./engine.js";
import { Keypad } from "./keypad.js";
import { numberLine } from "./numberline.js";
import { Graph } from "./graph.js";
import { History } from "./history.js";
import { speak } from "./speech.js";
import { LANGUAGE_KEY, language, onLanguageChange, pickLanguage, setLanguage, t } from "./i18n.js";

const STORAGE_KEY = "mathlint:last-solution";
const THEME_KEY = "mathlint:theme";

const $ = (id) => document.getElementById(id);
const status = $("status");
const checkButton = $("check");
const results = $("results");
const versionSlot = $("version");
const mathLines = $("math-lines");
const textSheet = $("text-sheet");
const solutionText = $("solution");
const gutter = $("gutter");
const modeToggle = $("mode-toggle");
const checkKeypadSlot = $("keypad-slot-check");
const stepsKeypadSlot = $("keypad-slot-steps");
const keypadRoot = $("keypad");
const operationGroup = $("operation");
const expressionBlock = $("expression-block");
const expressionField = $("expression");
const matrixBlock = $("matrix-block");
const matrixInput = $("matrix");
const bounds = $("bounds");
const lowerField = $("lower");
const upperField = $("upper");
const stepsButton = $("show-steps");
const stepsStatus = $("steps-status");
const targetLabel = $("target-label");
const targetHelp = $("target-help");
const worked = $("worked");
const equationLines = $("equation-lines");
const solveKeypadSlot = $("keypad-slot-solve");
const solveButton = $("solve-button");
const solveStatus = $("solve-status");
const solved = $("solved");
const liveAnswer = $("live-answer");
const textbookSelect = $("textbook-problems");
const textbookProblem = $("textbook-problem");
const textbookSource = $("textbook-source");
const enginePill = $("engine-pill");
const engineText = $("engine-text");
const examplesSheet = $("examples-sheet");
const exampleList = $("example-list");
const aboutSheet = $("about-sheet");
const historySheet = $("history-sheet");
const historyList = $("history-list");
const historyEmpty = $("history-empty");
const historyClear = $("history-clear");
const historyStore = new History();

// A phone-sized screen: the keypad docks at the bottom like a keyboard.
const COMPACT = window.matchMedia("(max-width: 899px)");

const MARKS = { OK: "✓", WRONG: "✗", WARNING: "!", UNSURE: "?" };

let engine = null;
let engineReady = false;
let examples = [];
let solveExamples = [];
let sheet = null;
let solveSheet = null;
let keypad = null;
let solveVariable = null;
let previewTimer = null;
let previewRound = 0;
let textMode = false;
let lastField = null;
let checkedAsMath = true;
let checkedOnce = false;
let workedOnce = false;

// ---------------------------------------------------------------- small helpers

function el(tag, className = "", text = null) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== null) element.textContent = text;
  return element;
}

function icon(name) {
  const wrapper = document.createElement("span");
  wrapper.innerHTML = `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;
  return wrapper.firstChild;
}

function card(className, title = null) {
  const box = el("article", "card " + className);
  if (title) {
    const head = el("header", "card-head");
    head.append(el("h2", "", title));
    box.append(head);
  }
  return box;
}

// ---------------------------------------------------------------- the engine pill

// `key` names the words, so they can be said again in another language.
function setEngineState(state, key) {
  enginePill.dataset.state = state;
  engineText.dataset.i18n = key;
  engineText.textContent = t(key);
}

// ---------------------------------------------------------------- the sheet

function drawGutter() {
  const count = Math.max(solutionText.value.split("\n").length, 6);
  gutter.textContent = Array.from({ length: count }, (_, i) => i + 1).join("\n");
  gutter.scrollTop = solutionText.scrollTop;
}

function currentText() {
  return textMode ? solutionText.value : sheet.getText();
}

function setText(text) {
  if (textMode) {
    solutionText.value = text;
    drawGutter();
  } else {
    sheet.setLines(text.split("\n"));
  }
}

function setTextMode(on) {
  if (on === textMode) return;
  if (on) {
    solutionText.value = sheet.getLines().join("\n");
  } else {
    sheet.setLines(solutionText.value.split("\n"));
  }
  textMode = on;
  mathLines.hidden = on;
  textSheet.hidden = !on;
  checkKeypadSlot.hidden = on;
  modeToggle.dataset.i18n = on ? "check.useKeypad" : "check.typeAsText";
  modeToggle.textContent = t(modeToggle.dataset.i18n);
  modeToggle.setAttribute("aria-pressed", String(on));
  drawGutter();
  if (on) {
    // from the start of the first line, not scrolled to the end of the last
    solutionText.setSelectionRange(0, 0);
    solutionText.focus();
    solutionText.scrollLeft = 0;
  } else {
    sheet.fields[0]?.focus();
  }
}

function initialText() {
  const hash = sharedText();
  if (hash) return hash;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return saved;
  } catch {
    /* private browsing: fall through to the example */
  }
  return examples.length ? examples[0].lines.join("\n") : "";
}

function sharedText() {
  return new URLSearchParams(location.hash.slice(1)).get("s");
}

function remember(text) {
  try {
    localStorage.setItem(STORAGE_KEY, text);
  } catch {
    /* nothing to do: the check still works */
  }
  const params = new URLSearchParams();
  params.set("s", text);
  history.replaceState(null, "", "#" + params.toString());
}

// ---------------------------------------------------------------- the keypad

function isVisible(element) {
  return Boolean(element) && element.isConnected && element.offsetParent !== null;
}

function isMathField(element) {
  return Boolean(element) && element.tagName === "MATH-FIELD";
}

function activeTab() {
  for (const name of ["solve", "check", "linalg"]) {
    if ($(`tab-${name}`).getAttribute("aria-selected") === "true") return name;
  }
  return "solve";
}

function keypadTarget() {
  const active = document.activeElement;
  if (isMathField(active) && isVisible(active)) return active;
  if (isVisible(lastField)) return lastField;
  const tab = activeTab();
  if (tab === "solve") return solveSheet.active || solveSheet.fields[0];
  return tab === "check" ? sheet.fields.at(-1) : expressionField;
}

function handleEnter(field) {
  const tutor = field.closest(".tutor-card");
  if (tutor) return tutor.requestSubmit();
  if (sheet.contains(field)) return sheet.newLineAfter(field);
  // on a phone the keypad steps aside so the answer can be seen
  if (COMPACT.matches) field.blur();
  if (solveSheet.contains(field)) solve({ reveal: true });
  else showSteps({ reveal: true });
}

// What the Enter key does, in words, for the field it will act on.
function enterLabel(field) {
  if (field.closest(".tutor-card")) return t("keypad.enterCheck");
  if (solveSheet.contains(field)) return t("keypad.enterSolve");
  if (sheet.contains(field)) return null;
  return t("keypad.enterGo");
}

function deleteEmptyLine(field) {
  for (const owner of [sheet, solveSheet]) {
    if (owner.contains(field) && owner.fields.length > 1) {
      owner.removeLine(field);
      return true;
    }
  }
  return false;
}

// On a phone the keypad is a dock that rises while a math field has focus.
function openKeypad(field) {
  keypad.refresh();
  if (!COMPACT.matches || document.body.classList.contains("keypad-open")) return;
  document.body.classList.add("keypad-open");
  // once the dock is up, keep the line being written above it
  setTimeout(() => field.scrollIntoView({ block: "center", behavior: "smooth" }), 220);
}

function closeKeypad() {
  document.body.classList.remove("keypad-open");
}

function watchKeypadFocus() {
  document.addEventListener("focusin", (event) => {
    const field = event.composedPath().find(isMathField);
    if (!field) return;
    lastField = field;
    openKeypad(field);
  });
  document.addEventListener("focusout", () => {
    // focus moving from one math field to the next passes through the body
    setTimeout(() => {
      if (!isMathField(document.activeElement)) closeKeypad();
    }, 0);
  });
  // a tap on the keypad's own background must not take the focus away
  keypadRoot.addEventListener("pointerdown", (event) => {
    if (!event.target.closest(".keypad-hide")) event.preventDefault();
  });
}

// ---------------------------------------------------------------- math on the page

// Math in words, in the reader's language, for screen readers.
function spoken(latex) {
  return speak(latex, (key, args) => t("speech." + key, args));
}

// Drawn with KaTeX for the eye; a screen reader hears the same math in words
// instead (MathML support differs too much between readers, above all on phones).
function renderMath(target, latex, displayMode = false) {
  if (!latex || !window.katex) {
    target.textContent = target.dataset.plain || "";
    return;
  }
  try {
    window.katex.render(latex, target, { throwOnError: false, displayMode });
    target.querySelector(".katex")?.setAttribute("aria-hidden", "true");
    target.append(el("span", "sr-only", spoken(latex)));
  } catch {
    target.textContent = target.dataset.plain || "";
  }
}

// A short sentence for screen readers when a result arrives.
function announce(text) {
  const announcer = $("announcer");
  announcer.textContent = "";
  // a change the reader's screen reader will notice, even for the same words
  setTimeout(() => (announcer.textContent = text), 50);
}

// Plain-text math (a practice problem) drawn as math.
function renderPlainMath(target, text) {
  target.dataset.plain = text;
  renderMath(target, displayLatex(toLatex(text)));
}

function renderFailure(target, message) {
  target.replaceChildren();
  const box = card("failure");
  box.setAttribute("role", "alert");
  const body = el("div", "failure-body");
  body.append(icon("about"), el("p", "", message));
  box.append(body);
  target.append(box);
}

// Math wider than its card scrolls sideways; a keyboard has to be able to reach
// it to scroll it, so such math takes the focus.
function reachableWhenWide(root) {
  requestAnimationFrame(() => {
    for (const math of root.querySelectorAll(".answer, .worked-math, .step-raw, .step-read")) {
      if (math.scrollWidth > math.clientWidth + 1) {
        math.tabIndex = 0;
        math.setAttribute("role", "group");
        math.setAttribute("aria-label", math.querySelector(".sr-only")?.textContent || "");
      }
    }
  });
}

// ---------------------------------------------------------------- running a request

// Run one engine request while showing a status and a Stop button.
async function run(kind, payload, { statusLine, button, stopButton, label, pane }) {
  statusLine.textContent = label;
  statusLine.classList.add("is-busy");
  button.disabled = true;
  stopButton.hidden = false;
  pane.setAttribute("aria-busy", "true");
  setEngineState("busy", "engine.working");
  try {
    return await engine.call(kind, payload);
  } finally {
    statusLine.textContent = engineReady ? "" : statusLine.textContent;
    statusLine.classList.remove("is-busy");
    button.disabled = false;
    stopButton.hidden = true;
    pane.removeAttribute("aria-busy");
    if (engineReady) setEngineState("ready", readyKey());
  }
}

// After a tap on Solve, bring the answer into view on a phone, and take the
// keyboard there when the tap was on a button (not while typing in a line).
function revealResults(target) {
  const first = target.firstElementChild;
  if (!first) return;
  if (document.activeElement?.tagName === "BUTTON") {
    first.tabIndex = -1;
    first.focus({ preventScroll: true });
  }
  if (COMPACT.matches) first.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------------------------------------------------------------- checking

function stepElement(step) {
  const verdict = step.verdict || "";
  const row = el("li", "verdict-line" + (verdict ? ` mark-${verdict.toLowerCase()}` : ""));

  const mark = el("div", "mark");
  const number = el("span", "mark-number", String(step.line));
  const symbol = el("b", "mark-symbol", MARKS[verdict] || "");
  if (verdict) symbol.setAttribute("aria-label", t("verdict." + verdict));
  mark.append(number, symbol);
  row.append(mark);

  const body = el("div", "verdict-body");

  const raw = el("div", "step-raw");
  raw.dataset.plain = step.raw;
  if (checkedAsMath) {
    raw.classList.add("as-math");
    renderMath(raw, displayLatex(step.raw));
  } else {
    raw.textContent = step.raw;
  }
  body.append(raw);

  const read = el("p", "step-read");
  const label = el("span", "", t("report.readsAs"));
  const math = el("span");
  math.dataset.plain = step.read_as;
  renderMath(math, step.read_as_latex);
  read.append(label, math);
  body.append(read);

  if (step.message) {
    const method = { exact: t("report.proved"), numeric: t("report.numeric") }[step.method] || "";
    body.append(el("p", "step-note " + verdict.toLowerCase(), step.message + method));
  }

  if (step.values && step.compared_to) {
    const at = step.counterexample
      ? Object.entries(step.counterexample).map(([name, value]) => `${name} = ${value}`).join(", ")
      : null;
    const evidence = el("div", "evidence");
    evidence.append(
      el("span", "evidence-label", at ? t("report.counterexampleAt", { point: at }) : t("report.counterexample"))
    );
    const values = el("span", "evidence-values");
    values.append(
      el("span", "", t("report.lineValue", { line: step.compared_to, value: step.values[0] })),
      el("span", "", t("report.lineValue", { line: step.line, value: step.values[1] }))
    );
    evidence.append(values);
    body.append(evidence);
  }

  for (const hint of step.hints || []) body.append(el("p", "hint", hint));
  for (const warning of step.warnings || []) body.append(el("p", "warn", warning));

  row.append(body);
  return row;
}

function renderReport(report) {
  results.replaceChildren();

  const error = report.steps.find((step) => step.verdict === "WRONG");
  const summary = card("summary-card " + (error ? "broken" : "clean"));
  const badge = el("span", "summary-badge", error ? "✗" : "✓");
  badge.setAttribute("aria-hidden", "true");
  const words = el("div", "summary");
  if (error) {
    words.append(
      el("strong", "", error.compared_to
        ? t("report.firstMistakePair", { from: error.compared_to, to: error.line })
        : t("report.firstMistake", { line: error.line })),
      el("span", "", error.compared_to ? t("report.aboveChecks") : t("report.lookAgain"))
    );
  } else {
    words.append(
      el("strong", "", t("report.noMistakes")),
      el("span", "", t("report.follows"))
    );
  }
  summary.append(badge, words);
  results.append(summary);

  const marked = card("report-card", report.mode === "equation" ? t("report.solving") : t("report.marked"));
  const list = el("ol", "verdict-lines");
  for (const step of report.steps) list.append(stepElement(step));
  marked.append(list);
  for (const note of report.notes || []) marked.append(el("p", "warn", note));
  results.append(marked);

  // the same marks, in the margin of the notebook
  if (checkedAsMath) {
    const verdicts = [];
    for (const step of report.steps) verdicts[step.line - 1] = step.verdict;
    sheet.setMarks(verdicts);
  }
}

// `record`: a check the reader asked for goes into the history; one run on
// their behalf (opening the tab, changing the language) does not.
async function check({ reveal = false, record = true } = {}) {
  if (!engineReady) return;
  checkedOnce = true;
  const text = currentText();
  checkedAsMath = !textMode;
  remember(text);
  const outcome = await run(
    "check",
    { text },
    { statusLine: status, button: checkButton, stopButton: $("stop-check"), label: t("check.busy"), pane: results }
  );
  if (outcome.ok) {
    renderReport(outcome.result);
    reachableWhenWide(results);
    announce(results.querySelector(".summary")?.textContent || "");
  } else {
    renderFailure(results, outcome.error);
    announce(outcome.error);
  }
  if (outcome.ok && record && text) {
    const error = outcome.result.steps.find((step) => step.verdict === "WRONG");
    historyStore.add({ tab: "check", input: text, extra: { mistake: error ? error.line : null, asMath: checkedAsMath } });
  }
  if (reveal) revealResults(results);
}

// ---------------------------------------------------------------- examples

function openSheet(dialog) {
  closeKeypad();
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function closeSheet(dialog) {
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

function setUpSheets() {
  for (const dialog of [examplesSheet, aboutSheet, historySheet]) {
    dialog.addEventListener("click", (event) => {
      // a tap on the backdrop, or on a close button
      if (event.target === dialog || event.target.closest("[data-close]")) closeSheet(dialog);
    });
  }
  $("open-about").addEventListener("click", () => openSheet(aboutSheet));
  $("open-history").addEventListener("click", openHistory);
  for (const input of document.querySelectorAll('input[name="history-filter"]')) {
    input.addEventListener("change", renderHistory);
  }
  historyClear.addEventListener("click", clearHistory);
  $("open-solve-examples").addEventListener("click", () => openExamples("solve"));
  $("open-check-examples").addEventListener("click", () => openExamples("check"));
}

function exampleButton(name, lines, onPick) {
  const button = el("button", "example");
  button.type = "button";
  button.append(el("span", "example-name", t("example." + name)));
  const math = el("span", "example-math");
  for (const line of lines) {
    const row = el("span", "example-line");
    row.dataset.plain = line;
    renderMath(row, displayLatex(line));
    math.append(row);
  }
  button.append(math);
  button.addEventListener("click", () => {
    closeSheet(examplesSheet);
    onPick();
  });
  return button;
}

function openExamples(context) {
  exampleList.replaceChildren();
  $("textbook-library").hidden = context !== "solve";
  $("examples-title").dataset.i18n = context === "solve" ? "examples.solve" : "examples.check";
  $("examples-title").textContent = t($("examples-title").dataset.i18n);

  if (context === "solve") {
    const groups = new Map();
    for (const example of solveExamples) {
      const group = example.group || "More";
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group).push(example);
    }
    for (const [group, list] of groups) {
      exampleList.append(el("h3", "example-group", group === "More" ? t("examples.more") : t("example." + group)));
      const grid = el("div", "example-grid");
      for (const example of list) {
        grid.append(
          exampleButton(example.name, example.lines, () => {
            solveSheet.setLines(example.lines);
            solveVariable = null;
            solve({ reveal: true });
          })
        );
      }
      exampleList.append(grid);
    }
  } else {
    const grid = el("div", "example-grid");
    for (const example of examples) {
      const shown = example.lines.slice(0, 2);
      grid.append(
        exampleButton(example.name, shown, () => {
          setText(example.lines.join("\n"));
          check({ reveal: true });
        })
      );
    }
    exampleList.append(grid);
  }
  openSheet(examplesSheet);
}

// ---------------------------------------------------------------- solving

async function solve(options = null) {
  // solve() and solve("factoring") are both still fine
  const { method = null, reveal = false, record = true } =
    typeof options === "string" ? { method: options } : options || {};
  const variable = solveVariable;
  if (!engineReady) return;
  // one line is an equation; several lines are a system
  const text = solveSheet.getText();
  if (!text) {
    renderFailure(solved, t("solve.empty"));
    return;
  }
  const outcome = await run(
    "solve",
    { text, method, variable },
    { statusLine: solveStatus, button: solveButton, stopButton: $("stop-solve"), label: t("solve.busy"), pane: solved }
  );
  if (outcome.ok) {
    renderSolved(outcome.result);
    reachableWhenWide(solved);
    const answer = outcome.result.answer_latex;
    announce(answer ? t("answer.announce", { answer: spoken(answer) }) : t("answer.whichLetter"));
  } else {
    renderFailure(solved, outcome.error);
    announce(outcome.error);
  }
  if (outcome.ok && record && !outcome.result.needs_letter) {
    const solution = outcome.result;
    historyStore.add({
      tab: "solve",
      input: text,
      kind: solution.kind_label,
      answer: solution.answer_latex,
      extra: { method, variable },
    });
  }
  if (reveal) revealResults(solved);
}

// ---------------------------------------------------------------- the live answer

const PREVIEW_PAUSE_MS = 450;
const PREVIEW_LIMIT_MS = 4000;

// A short pause in typing asks the engine for the answer alone.
function schedulePreview() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(preview, PREVIEW_PAUSE_MS);
}

async function preview() {
  const round = ++previewRound;
  const text = solveSheet.getText();
  if (!text || !engineReady) return showPreview(null);
  // a Solve that is running comes first; ask again once it is done
  if (engine.busy) return schedulePreview();
  const outcome = await engine.call(
    "preview",
    { text },
    { timeLimit: PREVIEW_LIMIT_MS, quiet: true }
  );
  if (round !== previewRound) return; // typing went on in the meantime
  showPreview(outcome.ok ? outcome.result : null);
}

function showPreview(result) {
  if (!result || !result.latex) {
    liveAnswer.replaceChildren();
    liveAnswer.hidden = true;
    return;
  }
  const latex = result.decimal_latex
    ? `${result.latex} \\qquad ${result.decimal_latex}`
    : result.latex;
  const math = el("span", "live-math");
  renderMath(math, latex);
  liveAnswer.replaceChildren(el("span", "live-tag", t("answer.live")), math);
  liveAnswer.hidden = false;
}

// A row of chips; the chosen one is pressed.
function chipGroup(label, items) {
  const chips = el("div", "chip-group");
  chips.setAttribute("role", "group");
  chips.setAttribute("aria-label", label);
  chips.append(el("span", "chip-label", label));
  const row = el("div", "chip-row");
  for (const { text, pressed, onClick } of items) {
    const chip = el("button", "chip", text);
    chip.type = "button";
    chip.setAttribute("aria-pressed", String(pressed));
    chip.addEventListener("click", onClick);
    row.append(chip);
  }
  chips.append(row);
  return chips;
}

// Chips for the letter to solve for; the chosen one is pressed.
function letterChips(letters, current, label) {
  return chipGroup(
    label,
    letters.map((letter) => ({
      text: letter,
      pressed: letter === current,
      onClick: () => {
        solveVariable = letter;
        solve();
      },
    }))
  );
}

function renderSolved(solution) {
  solved.replaceChildren();
  const answerCard = card("answer-card");
  solved.append(answerCard);

  if (solution.needs_letter) {
    answerCard.append(el("p", "eyebrow", t("answer.severalLetters")));
    answerCard.append(
      el("p", "answer-question", t("answer.whichLetter")),
      letterChips(solution.letters, null, t("answer.solveFor"))
    );
    return;
  }

  const found = solution.answers.length || solution.everything;
  const head = el("div", "answer-head");
  head.append(el("p", "eyebrow solved-kind", solution.kind_label));
  if (found) {
    const verified = el("span", "answer-badge", t("answer.checked"));
    verified.prepend(icon("shield"));
    verified.title = t("answer.checkedTitle");
    head.append(verified);
  }
  answerCard.append(head);

  const answer = el("div", "answer" + (found ? "" : " none"));
  answer.dataset.plain = solution.answer_text;
  renderMath(answer, solution.answer_latex, true);
  answerCard.append(answer);

  // an inequality: the same answer in interval notation, and on a number line
  if (solution.interval_latex && solution.number_line && !solution.everything) {
    const intervals = el("p", "answer-note");
    intervals.dataset.plain = solution.interval_text;
    renderMath(intervals, String.raw`\text{${t("answer.thatIs")} } ` + solution.interval_latex);
    answerCard.append(intervals);
    if (solution.number_line.intervals.length || solution.number_line.points.length) {
      answerCard.append(numberLine(solution.number_line, renderMath));
    }
  }

  // the exact answer stays first; the decimal is what a calculator would say
  if (solution.decimal_latex) {
    const decimal = el("p", "answer-note answer-decimal");
    decimal.dataset.plain = t("answer.about", { value: solution.decimal });
    renderMath(decimal, solution.decimal_latex);
    answerCard.append(decimal);
  }

  // what the answer is only true for, such as x != -2 after cancelling (x + 2)
  if (solution.conditions && solution.conditions.length) {
    const conditions = solution.conditions.join(", ").replaceAll("!=", "≠");
    answerCard.append(el("p", "answer-note", t("answer.for", { conditions })));
  }

  // a letter to solve for only makes sense for an equation
  if (solution.variable && solution.letters && solution.letters.length > 1) {
    answerCard.append(letterChips(solution.letters, solution.variable, t("answer.solveFor")));
  }

  if (solution.methods.length > 1) {
    const verb = solution.variable || solution.unknowns ? t("answer.solveItBy") : t("answer.method");
    answerCard.append(
      chipGroup(
        verb,
        solution.methods.map((method) => ({
          text: method.label,
          pressed: method.id === solution.method,
          onClick: () => solve(method.id),
        }))
      )
    );
  }

  if (solution.graph) solved.append(graphSection(solution.graph));

  const steps = card("steps-card", t("card.steps"));
  solved.append(steps);
  renderLearningSteps(steps, solution);
  if (solution.practice && solution.practice.length) {
    solved.append(practiceSection(solution.practice));
  }
}

function loadIntoSolver(text, method) {
  const lines = text.split(/\s*;\s*|\n/).filter(Boolean);
  solveSheet.setLines(lines);
  solveVariable = null;
  selectTab("solve");
  solve({ method, reveal: false });
  equationLines.scrollIntoView({ block: "center", behavior: "smooth" });
}

function fillTextbookProblems(problems) {
  for (const [index, problem] of problems.entries()) {
    const option = document.createElement("option");
    option.value = String(index);
    option.dataset.section = problem.section;
    option.dataset.exercise = problem.exercise;
    option.textContent = t("textbook.exercise", { section: problem.section, exercise: problem.exercise });
    textbookSelect.append(option);
  }

  function selected() {
    return problems[Number(textbookSelect.value)];
  }

  function showSelection() {
    const problem = selected();
    textbookProblem.textContent = problem.text.replaceAll(";", "  ·  ");
    textbookSource.href = problem.source;
  }

  textbookSelect.addEventListener("change", showSelection);
  $("solve-textbook").addEventListener("click", () => {
    const problem = selected();
    closeSheet(examplesSheet);
    loadIntoSolver(problem.text, problem.method || null);
  });
  showSelection();
}

function practiceSection(problems) {
  const section = card("practice-card", t("practice.title"));
  section.append(el("p", "card-intro", t("practice.intro")));
  const list = el("div", "practice-list");

  for (const problem of problems) {
    const button = el("button", "practice-problem");
    button.type = "button";
    button.append(el("span", "practice-label", problem.label));
    const math = el("span", "practice-math");
    for (const line of problem.text.split(/\s*;\s*|\n/).filter(Boolean)) {
      const row = el("span", "practice-line");
      renderPlainMath(row, line);
      math.append(row);
    }
    button.append(math);
    const go = el("span", "practice-go", t("practice.go"));
    go.append(icon("arrow"));
    button.append(go);
    button.addEventListener("click", () => {
      const lines = problem.text.split(/\s*;\s*|\n/).filter(Boolean);
      solveSheet.setLines(lines);
      solveVariable = null;
      solve(problem.method || null);
      equationLines.scrollIntoView({ block: "center", behavior: "smooth" });
    });
    list.append(button);
  }
  section.append(list);
  return section;
}

function graphSection(spec) {
  const section = card("graph-card", t("card.graph"));
  const graph = new Graph(spec, {
    renderMath,
    fetchSamples: async (xMin, xMax) => {
      const outcome = await engine.call(
        "plot",
        { curves: spec.curves.map((curve) => curve.expr), variable: spec.variable, x_min: xMin, x_max: xMax },
        { timeLimit: PREVIEW_LIMIT_MS, quiet: true }
      );
      return outcome.ok ? outcome.result : null;
    },
  });
  section.append(graph.element);
  return section;
}

// ---------------------------------------------------------------- worked solutions

function operationValue() {
  return operationGroup.querySelector("input:checked").value;
}

function isCalculus(operation) {
  return operation === "diff" || operation === "integrate";
}

function updateOperationInput() {
  const operation = operationValue();
  const calculus = isCalculus(operation);
  expressionBlock.hidden = !calculus;
  matrixBlock.hidden = calculus;
  bounds.hidden = operation !== "integrate";
  stepsKeypadSlot.hidden = !calculus;
  targetLabel.dataset.i18n = calculus ? "workout.expression" : "workout.matrix";
  targetLabel.textContent = t(targetLabel.dataset.i18n);
  targetHelp.dataset.i18n = calculus ? "workout.expressionHelp" : "workout.matrixHelp";
  targetHelp.textContent = t(targetHelp.dataset.i18n);
}

function workedStep(step, index) {
  const row = el("li", "worked-step");
  row.append(el("div", "worked-index", String(index + 1)));

  const body = el("div", "worked-body");
  const text = el("p", "worked-text", step.text);
  if (step.operation) text.append(el("span", "worked-operation", step.operation));
  body.append(text);

  if (step.math_latex || step.math) {
    const math = el("div", "worked-math");
    math.dataset.plain = step.math;
    renderMath(math, step.math_latex);
    body.append(math);
  }

  if (step.why) body.append(whyDetails(step.why));

  row.append(body);
  return row;
}

function whyDetails(why) {
  const details = el("details", "step-why");
  const summary = document.createElement("summary");
  summary.textContent = t("steps.why");
  summary.prepend(icon("bulb"));
  details.append(summary);

  const entries = [
    ["rule", why.rule],
    ["example", why.example],
    ["mistake", why.mistake],
  ];
  const panel = el("div", "why-panel");
  for (const [part, value] of entries) {
    const paragraph = el("p", "why-" + part);
    const heading = el("strong", "", t("steps." + part));
    paragraph.append(heading, el("span", "", value));
    panel.append(paragraph);
  }
  details.append(panel);
  return details;
}

function tutorText(value) {
  // MathLive turns a typed "or" into logical-or. The document parser uses the
  // words "or" to separate several solutions, so keep that intent explicit.
  return value.replaceAll(String.raw`\lor`, String.raw`\text{ or }`).replaceAll("∨", " or ");
}

function renderLearningSteps(target, solution) {
  const steps = solution.steps || [];
  if (!steps.length) return;

  const learning = el("section", "learning-steps");
  const meter = el("div", "step-meter");
  const progress = el("p", "step-progress");
  progress.setAttribute("aria-live", "polite");
  const bar = el("div", "step-bar");
  bar.setAttribute("aria-hidden", "true");
  const fill = el("span");
  bar.append(fill);
  meter.append(progress, bar);

  const toolbar = el("div", "learning-toolbar");
  const reveal = el("button", "primary learning-button", t("steps.reveal"));
  reveal.type = "button";
  const tryNext = el("button", "tonal learning-button", t("steps.try"));
  tryNext.type = "button";
  tryNext.prepend(icon("sparkle"));
  const showAll = el("button", "ghost-button learning-button", t("steps.showAll"));
  showAll.type = "button";
  toolbar.append(reveal, tryNext, showAll);

  const rows = el("ol", "worked-steps");
  const elements = steps.map((step, index) => workedStep(step, index));
  elements.forEach((element) => rows.append(element));

  const tutor = el("form", "tutor-card");
  tutor.hidden = true;
  tutor.setAttribute("aria-label", t("tutor.label"));
  const tutorLabel = el("label", "", t("tutor.prompt"));
  const tutorField = document.createElement("math-field");
  tutorField.setAttribute("aria-label", t("tutor.field"));
  tutorLabel.append(tutorField);
  const tutorActions = el("div", "tutor-actions");
  const checkStep = el("button", "primary learning-button", t("tutor.check"));
  checkStep.type = "submit";
  const cancelTutor = el("button", "ghost-button learning-button", t("common.cancel"));
  cancelTutor.type = "button";
  tutorActions.append(checkStep, cancelTutor);
  const feedback = el("p", "tutor-feedback");
  feedback.setAttribute("role", "status");
  feedback.setAttribute("aria-live", "polite");
  tutor.append(tutorLabel, feedback, tutorActions);

  learning.append(meter, rows, tutor, toolbar);
  target.append(learning);
  configureField(tutorField);

  let shown = 1;
  let tutorTarget = -1;

  function nextMathIndex() {
    return steps.findIndex((step, index) => index >= shown && (step.math_latex || step.math));
  }

  function previousMathIndex(index) {
    for (let previous = index - 1; previous >= 0; previous -= 1) {
      if (steps[previous].math_latex || steps[previous].math) return previous;
    }
    return -1;
  }

  function update() {
    elements.forEach((element, index) => (element.hidden = index >= shown));
    progress.textContent = t("steps.progress", { shown: Math.min(shown, steps.length), total: steps.length });
    fill.style.width = `${(Math.min(shown, steps.length) / steps.length) * 100}%`;
    reveal.hidden = shown >= steps.length;
    showAll.hidden = shown >= steps.length;
    const next = nextMathIndex();
    tryNext.hidden = shown >= steps.length || next < 0 || previousMathIndex(next) < 0;
    toolbar.hidden = shown >= steps.length;
    if (shown >= steps.length) tutor.hidden = true;
  }

  function revealThrough(index) {
    const oldShown = shown;
    shown = Math.min(steps.length, index + 1);
    update();
    for (let current = oldShown; current < shown; current += 1) {
      const element = elements[current];
      element.classList.add("step-enter");
      element.addEventListener("animationend", () => element.classList.remove("step-enter"), {
        once: true,
      });
    }
    reachableWhenWide(learning);
  }

  reveal.addEventListener("click", () => revealThrough(shown));
  showAll.addEventListener("click", () => revealThrough(steps.length - 1));
  tryNext.addEventListener("click", () => {
    tutorTarget = nextMathIndex();
    if (tutorTarget < 0) return;
    tutor.hidden = false;
    tutor.dataset.result = "";
    feedback.textContent = t("tutor.aim", { step: tutorTarget + 1 });
    tutorField.value = "";
    tutorField.focus();
  });
  cancelTutor.addEventListener("click", () => {
    tutor.hidden = true;
    tryNext.focus();
  });
  tutor.addEventListener("submit", async (event) => {
    event.preventDefault();
    const attempt = tutorText(tutorField.value.trim());
    const previous = previousMathIndex(tutorTarget);
    if (!attempt || tutorTarget < 0 || previous < 0) {
      feedback.textContent = t("tutor.empty");
      return;
    }

    checkStep.disabled = true;
    feedback.textContent = t("tutor.checking");
    tutor.dataset.result = "";
    const outcome = await engine.call("tutor", {
      previous: steps[previous].math,
      expected: steps[tutorTarget].math,
      attempt,
    });
    checkStep.disabled = false;
    if (!outcome.ok) {
      feedback.textContent = outcome.error;
      return;
    }
    const checked = outcome.result;
    if (checked.accepted) {
      const note = checked.verdict === "WARNING" ? ` ${checked.message}` : "";
      feedback.textContent = t("tutor.yes") + note;
      revealThrough(tutorTarget);
      tutor.hidden = true;
      elements[tutorTarget].tabIndex = -1;
      elements[tutorTarget].focus();
      return;
    }
    const hint = checked.hints && checked.hints.length ? " " + t("tutor.hint", { hint: checked.hints[0] }) : "";
    tutor.dataset.result = "wrong";
    feedback.textContent = checked.message + hint;
  });

  update();
}

function renderSolution(solution) {
  worked.replaceChildren();
  const box = card("steps-card", solution.title);
  // on the page first: the tutor's math field can only be set up once it is
  worked.append(box);
  renderLearningSteps(box, solution);
  if (solution.summary) {
    const summary = el("p", "worked-summary", solution.summary);
    summary.prepend(icon("sparkle"));
    box.append(summary);
  }
}

async function showSteps({ reveal = false, record = true } = {}) {
  if (!engineReady) return;
  workedOnce = true;
  const operation = operationValue();
  const calculus = isCalculus(operation);
  const lower = operation === "integrate" ? lowerField.value.trim() : "";
  const upper = operation === "integrate" ? upperField.value.trim() : "";
  if (Boolean(lower) !== Boolean(upper)) {
    renderFailure(worked, t("workout.bothLimits"));
    return;
  }
  const target = calculus ? expressionField.value : matrixInput.value;
  const outcome = await run(
    "steps",
    { operation, target, lower, upper },
    { statusLine: stepsStatus, button: stepsButton, stopButton: $("stop-steps"), label: t("workout.busy"), pane: worked }
  );
  if (outcome.ok) {
    renderSolution(outcome.result);
    reachableWhenWide(worked);
    announce(outcome.result.summary || outcome.result.title);
  } else {
    renderFailure(worked, outcome.error);
    announce(outcome.error);
  }
  if (outcome.ok && record && target.trim()) {
    historyStore.add({
      tab: "linalg",
      input: target,
      kind: outcome.result.title,
      answer: outcome.result.result_latex || "",
      extra: { operation, lower, upper },
    });
  }
  if (reveal) revealResults(worked);
}

// ---------------------------------------------------------------- history

function openHistory() {
  renderHistory();
  openSheet(historySheet);
}

function historyFilter() {
  return document.querySelector('input[name="history-filter"]:checked')?.value || "all";
}

function when(time) {
  const seconds = Math.round((time - Date.now()) / 1000);
  const format = new Intl.RelativeTimeFormat(language(), { numeric: "auto" });
  for (const [unit, size] of [["year", 31536000], ["month", 2592000], ["week", 604800], ["day", 86400], ["hour", 3600], ["minute", 60]]) {
    if (Math.abs(seconds) >= size) return format.format(Math.round(seconds / size), unit);
  }
  return format.format(0, "second");
}

function historyEntry(entry) {
  const row = el("li", "history-entry");
  const open = el("button", "history-open");
  open.type = "button";
  const tabName = { solve: t("tab.solve"), check: t("tab.check"), linalg: t("tab.workout") }[entry.tab];
  const meta = [tabName, entry.kind, when(entry.time)].filter(Boolean).join(" · ");
  open.append(el("span", "history-meta", meta));
  for (const line of entry.input.split("\n").slice(0, 3)) {
    const math = el("span", "history-line");
    math.dataset.plain = line;
    if (entry.tab === "check" && entry.extra && entry.extra.asMath === false) math.textContent = line;
    else renderMath(math, displayLatex(entry.tab === "linalg" ? toLatex(line) : line));
    open.append(math);
  }
  if (entry.tab === "check") {
    const mistake = entry.extra && entry.extra.mistake;
    open.append(
      el(
        "span",
        "history-answer " + (mistake ? "mark-wrong" : "mark-ok"),
        mistake ? "✗ " + t("report.firstMistake", { line: mistake }) : "✓ " + t("report.noMistakes")
      )
    );
  } else if (entry.answer) {
    const answer = el("span", "history-answer");
    renderMath(answer, entry.answer);
    open.append(answer);
  }
  open.addEventListener("click", () => {
    closeSheet(historySheet);
    reopen(entry);
  });

  const star = el("button", "icon-button history-star");
  star.type = "button";
  star.append(icon("star"));
  star.setAttribute("aria-pressed", String(entry.starred));
  star.setAttribute("aria-label", t(entry.starred ? "history.unstar" : "history.star"));
  star.title = star.getAttribute("aria-label");
  star.addEventListener("click", () => {
    historyStore.star(entry.id, !entry.starred);
    renderHistory();
    historyList.querySelector(`[data-id="${entry.id}"] .history-star`)?.focus();
  });

  const remove = el("button", "icon-button history-delete");
  remove.type = "button";
  remove.append(icon("trash"));
  remove.setAttribute("aria-label", t("history.delete"));
  remove.title = t("history.delete");
  remove.addEventListener("click", () => {
    historyStore.remove(entry.id);
    renderHistory();
    historyList.querySelector(".history-open")?.focus();
  });

  row.dataset.id = entry.id;
  row.append(open, star, remove);
  return row;
}

function renderHistory() {
  const starredOnly = historyFilter() === "starred";
  const entries = historyStore.list({ starred: starredOnly });
  historyList.replaceChildren(...entries.map(historyEntry));
  const available = historyStore.available;
  historyEmpty.hidden = entries.length > 0;
  historyEmpty.textContent = !available
    ? t("history.unavailable")
    : starredOnly
      ? t("history.noStarred")
      : t("history.empty");
  historyClear.hidden = !historyStore.list().some((entry) => !entry.starred);
  historyClear.classList.remove("confirming");
  historyClear.textContent = t("history.clear");
}

// Clearing asks once more; starred entries stay.
let clearTimer = null;
function clearHistory() {
  if (!historyClear.classList.contains("confirming")) {
    historyClear.classList.add("confirming");
    historyClear.textContent = t("history.confirmClear");
    clearTimeout(clearTimer);
    clearTimer = setTimeout(renderHistory, 4000);
    return;
  }
  clearTimeout(clearTimer);
  historyStore.clear();
  renderHistory();
}

function reopen(entry) {
  const extra = entry.extra || {};
  if (entry.tab === "solve") {
    solveSheet.setLines(entry.input.split("\n"));
    selectTab("solve");
    solveVariable = extra.variable || null;
    solve({ method: extra.method || null, reveal: true });
  } else if (entry.tab === "check") {
    checkedOnce = true;
    selectTab("check");
    setTextMode(extra.asMath === false);
    setText(entry.input);
    check({ reveal: true });
  } else {
    workedOnce = true;
    const radio = operationGroup.querySelector(`input[value="${extra.operation}"]`);
    if (radio) radio.checked = true;
    updateOperationInput();
    if (isCalculus(extra.operation)) expressionField.value = entry.input;
    else matrixInput.value = entry.input;
    lowerField.value = extra.lower || "";
    upperField.value = extra.upper || "";
    selectTab("linalg");
    showSteps({ reveal: true });
  }
}

// ---------------------------------------------------------------- the app shell

const TABS = [
  { name: "solve", panel: "panel-solve", slot: () => solveKeypadSlot },
  { name: "check", panel: "panel-check", slot: () => checkKeypadSlot },
  { name: "linalg", panel: "panel-linalg", slot: () => stepsKeypadSlot },
];

function selectTab(name, { focus = false } = {}) {
  closeKeypad();
  for (const entry of TABS) {
    const selected = entry.name === name;
    const tab = $(`tab-${entry.name}`);
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    $(entry.panel).hidden = !selected;
    if (selected) {
      entry.slot().append(keypadRoot);
      if (focus) tab.focus();
    }
  }
  document.body.dataset.tab = name;
  window.scrollTo({ top: 0 });
  keypad?.refresh();
  // the other tabs run their example the first time they are opened
  if (name === "check" && engineReady && !checkedOnce) check({ record: false });
  if (name === "linalg" && engineReady && !workedOnce) showSteps({ record: false });
}

function setUpTabs() {
  TABS.forEach((entry, index) => {
    const tab = $(`tab-${entry.name}`);
    tab.addEventListener("click", () => selectTab(entry.name));
    // arrow keys move along the tabs, as in any tab list
    tab.addEventListener("keydown", (event) => {
      const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
      if (!step) return;
      event.preventDefault();
      selectTab(TABS[(index + step + TABS.length) % TABS.length].name, { focus: true });
    });
  });
  $("panel-linalg").hidden = true;
}

function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "light" || theme === "dark") root.dataset.theme = theme;
  else delete root.dataset.theme;
  try {
    if (theme === "light" || theme === "dark") localStorage.setItem(THEME_KEY, theme);
    else localStorage.removeItem(THEME_KEY);
  } catch {
    /* the choice lasts until the page is closed */
  }
  // the browser's own bar follows the page
  const background = getComputedStyle(document.body).backgroundColor;
  for (const meta of document.querySelectorAll('meta[name="theme-color"]')) {
    if (!meta.dataset.original) meta.dataset.original = meta.content;
    meta.content = theme === "light" || theme === "dark" ? background : meta.dataset.original;
  }
}

function setUpLanguage() {
  for (const input of document.querySelectorAll('input[name="language"]')) {
    input.checked = input.value === language();
    input.addEventListener("change", () => setLanguage(input.value));
  }
  onLanguageChange(() => {
    for (const input of document.querySelectorAll('input[name="language"]')) {
      input.checked = input.value === language();
    }
    for (const option of textbookSelect.options) {
      const { section, exercise } = option.dataset;
      option.textContent = t("textbook.exercise", { section, exercise });
    }
    keypad?.render();
    solveSheet?.relabel(t("solve.line"));
    sheet?.relabel(t("check.line"));
    // the other fields' names were just said again on the host: move them in
    for (const field of document.querySelectorAll("math-field")) nameField(field);
    // what is on the screen is said again in the new language
    if (!engineReady) return;
    if (solved.childElementCount) solve({ record: false });
    if (checkedOnce) check({ record: false });
    if (workedOnce) showSteps({ record: false });
    if (historySheet.open) renderHistory();
  });
}

function setUpTheme() {
  const current = document.documentElement.dataset.theme || "system";
  for (const input of document.querySelectorAll('input[name="theme"]')) {
    input.checked = input.value === current;
    input.addEventListener("change", () => applyTheme(input.value));
  }
  if (current !== "system") applyTheme(current);
}

// ---------------------------------------------------------------- start-up

// ---------------------------------------------------------------- offline

// sw.js keeps the whole app, engine included, on the device. A new version
// installs quietly and waits until the reader chooses to reload.
function setUpOffline() {
  const state = $("offline-state");
  const toast = $("update-toast");
  const say = (key) => {
    state.dataset.i18n = key;
    state.textContent = t(key);
  };
  if (!("serviceWorker" in navigator)) return say("offline.unsupported");
  let reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    // a reload only when the reader asked for the new version
    if (reloading) location.reload();
  });
  const offer = (worker) => {
    toast.hidden = false;
    $("update-reload").onclick = () => {
      reloading = true;
      worker.postMessage("skip-waiting");
    };
  };
  navigator.serviceWorker
    .register("sw.js")
    .then((registration) => {
      if (registration.waiting && navigator.serviceWorker.controller) offer(registration.waiting);
      registration.addEventListener("updatefound", () => {
        const next = registration.installing;
        next?.addEventListener("statechange", () => {
          if (next.state === "installed" && navigator.serviceWorker.controller) offer(next);
        });
      });
      return navigator.serviceWorker.ready;
    })
    .then(() => say("offline.ready"))
    .catch(() => say("offline.unsupported"));
}

function savedLanguage() {
  try {
    return localStorage.getItem(LANGUAGE_KEY);
  } catch {
    return null;
  }
}

// The engine pill's word for "ready": it says so when the device is offline.
function readyKey() {
  return navigator.onLine === false ? "engine.readyOffline" : "engine.ready";
}

async function boot() {
  try {
    await setLanguage(pickLanguage(savedLanguage(), navigator.languages || [navigator.language]), {
      save: false,
    });
  } finally {
    document.documentElement.classList.remove("translating");
  }
  setUpTabs();
  setUpSheets();
  setUpTheme();
  setUpLanguage();
  setUpOffline();
  await customElements.whenDefined("math-field");

  for (const field of [expressionField, lowerField, upperField]) configureField(field);
  solveSheet = new MathSheet(equationLines, {
    onEnter: () => solve({ reveal: true }),
    // a new equation means the letter has to be chosen again
    onChange: () => {
      solveVariable = null;
      schedulePreview();
    },
    lineLabel: t("solve.line"),
  });
  $("add-equation").addEventListener("click", () => solveSheet.addLine());
  expressionField.value = String.raw`x^2\sin x`;

  sheet = new MathSheet(mathLines, { lineLabel: t("check.line") });
  keypad = new Keypad(keypadRoot, {
    getTarget: keypadTarget,
    onEnter: handleEnter,
    enterLabel,
    onDeleteEmpty: deleteEmptyLine,
    onHide: () => document.activeElement?.blur?.(),
  });
  solveKeypadSlot.append(keypadRoot);
  watchKeypadFocus();

  window.addEventListener(
    "keydown",
    (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        event.stopImmediatePropagation();
        const tab = activeTab();
        if (tab === "solve") solve({ reveal: true });
        else if (tab === "check") check({ reveal: true });
        else showSteps({ reveal: true });
      }
    },
    true
  );

  solveExamples = await fetch("solve-examples.json").then((response) => response.json());
  solveSheet.setLines(solveExamples[0].lines);

  const textbookProblems = await fetch("textbook-problems.json").then((response) => response.json());
  fillTextbookProblems(textbookProblems);

  examples = await fetch("examples.json").then((response) => response.json());
  setText(initialText());

  modeToggle.addEventListener("click", () => setTextMode(!textMode));
  solutionText.addEventListener("input", drawGutter);
  solutionText.addEventListener("scroll", () => (gutter.scrollTop = solutionText.scrollTop));
  checkButton.addEventListener("click", () => check({ reveal: true }));
  solveButton.addEventListener("click", () => solve({ reveal: true }));
  stepsButton.addEventListener("click", () => showSteps({ reveal: true }));
  for (const input of operationGroup.querySelectorAll("input")) {
    input.addEventListener("change", () => {
      updateOperationInput();
      if (engineReady) showSteps({ record: false });
    });
  }
  updateOperationInput();

  const stop = () => engine.stop(t("engine.stopped"));
  $("stop-check").addEventListener("click", stop);
  $("stop-solve").addEventListener("click", stop);
  $("stop-steps").addEventListener("click", stop);

  // a shared link to someone's working opens on the Check tab
  if (sharedText()) selectTab("check");

  setEngineState("loading", "engine.loading");
  engine = new Engine({
    onStatus: (key) => {
      for (const line of [status, solveStatus, stepsStatus]) {
        line.dataset.i18n = key;
        line.textContent = t(key);
      }
    },
  });
  const version = await engine.ready;
  engineReady = true;
  // seconds from opening the page to a working engine, shown in About
  const ready = performance.mark("mathlint:engine-ready");
  const showStartup = () =>
    ($("startup").textContent = t("about.startup", { seconds: (ready.startTime / 1000).toFixed(1) }));
  showStartup();
  onLanguageChange(showStartup);
  versionSlot.textContent = "mathlint " + version;
  setEngineState("ready", readyKey());
  for (const event of ["online", "offline"]) {
    window.addEventListener(event, () => {
      if (enginePill.dataset.state === "ready") setEngineState("ready", readyKey());
    });
  }
  enginePill.title = t("engine.title", { version });
  onLanguageChange(() => (enginePill.title = t("engine.title", { version })));
  for (const line of [status, solveStatus, stepsStatus]) delete line.dataset.i18n;
  for (const line of [status, solveStatus, stepsStatus]) line.textContent = "";
  checkButton.disabled = false;
  stepsButton.disabled = false;
  solveButton.disabled = false;
  await solve({ record: false });
  if (activeTab() === "check") await check({ record: false });
  warmUp();
}

// While the reader looks at the first answer, the engine loads what the other
// kinds of problem need, so their first answer comes sooner.
function warmUp() {
  const idle = window.requestIdleCallback || ((callback) => setTimeout(callback, 1000));
  idle(async () => {
    const outcome = await engine.call("warm", {}, { quiet: true, timeLimit: 60000 });
    if (outcome.ok) performance.mark("mathlint:warm", { detail: outcome.result });
  });
}

boot().catch((error) => {
  setEngineState("error", "engine.failed");
  for (const line of [status, solveStatus, stepsStatus]) line.textContent = t("engine.cannotStart");
  for (const target of [solved, results]) {
    renderFailure(target, t("engine.loadFailed", { error: error.message }));
  }
});
