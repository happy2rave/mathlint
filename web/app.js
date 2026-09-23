import { MathSheet, configureField, displayLatex, toLatex } from "./editor.js";
import { Engine } from "./engine.js";
import { Keypad } from "./keypad.js";
import { numberLine } from "./numberline.js";
import { Graph } from "./graph.js";

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

// A phone-sized screen: the keypad docks at the bottom like a keyboard.
const COMPACT = window.matchMedia("(max-width: 899px)");

const MARKS = { OK: "✓", WRONG: "✗", WARNING: "!", UNSURE: "?" };
const VERDICT_WORDS = { OK: "Correct", WRONG: "Wrong", WARNING: "Careful", UNSURE: "Not sure" };
const EXPRESSION_HELP =
  "Tap the keys or type it: x^2 sin x, e^(2x), 1/(x^2+1). The variable is picked up from the expression.";
const MATRIX_HELP =
  "Write it as [[2, 1], [3, 4]], MATLAB style [2 1; 3 4], or as a LaTeX pmatrix. " +
  "Fractions stay exact — no decimals.";

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

function setEngineState(state, text) {
  enginePill.dataset.state = state;
  engineText.textContent = text;
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
  modeToggle.textContent = on ? "Use the keypad" : "Type as text";
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
  if (field.closest(".tutor-card")) return "Check";
  if (solveSheet.contains(field)) return "Solve";
  if (sheet.contains(field)) return null;
  return "Go";
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

function renderMath(target, latex, displayMode = false) {
  if (!latex || !window.katex) {
    target.textContent = target.dataset.plain || "";
    return;
  }
  try {
    window.katex.render(latex, target, { throwOnError: false, displayMode });
  } catch {
    target.textContent = target.dataset.plain || "";
  }
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

// ---------------------------------------------------------------- running a request

// Run one engine request while showing a status and a Stop button.
async function run(kind, payload, { statusLine, button, stopButton, label, pane }) {
  statusLine.textContent = label;
  statusLine.classList.add("is-busy");
  button.disabled = true;
  stopButton.hidden = false;
  pane.setAttribute("aria-busy", "true");
  setEngineState("busy", "Working");
  try {
    return await engine.call(kind, payload);
  } finally {
    statusLine.textContent = engineReady ? "" : statusLine.textContent;
    statusLine.classList.remove("is-busy");
    button.disabled = false;
    stopButton.hidden = true;
    pane.removeAttribute("aria-busy");
    if (engineReady) setEngineState("ready", "Ready");
  }
}

// After a tap on Solve, bring the answer into view on a phone.
function revealResults(target) {
  if (!COMPACT.matches) return;
  const first = target.firstElementChild;
  if (first) first.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------------------------------------------------------------- checking

function stepElement(step) {
  const verdict = step.verdict || "";
  const row = el("li", "verdict-line" + (verdict ? ` mark-${verdict.toLowerCase()}` : ""));

  const mark = el("div", "mark");
  const number = el("span", "mark-number", String(step.line));
  const symbol = el("b", "mark-symbol", MARKS[verdict] || "");
  if (verdict) symbol.setAttribute("aria-label", VERDICT_WORDS[verdict]);
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
  const label = el("span", "", "reads as ");
  const math = el("span");
  math.dataset.plain = step.read_as;
  renderMath(math, step.read_as_latex);
  read.append(label, math);
  body.append(read);

  if (step.message) {
    const method = { exact: " (proved exactly)", numeric: " (checked with numbers)" }[step.method] || "";
    body.append(el("p", "step-note " + verdict.toLowerCase(), step.message + method));
  }

  if (step.values && step.compared_to) {
    const at = step.counterexample
      ? Object.entries(step.counterexample).map(([name, value]) => `${name} = ${value}`).join(", ")
      : null;
    const evidence = el("div", "evidence");
    evidence.append(el("span", "evidence-label", at ? `Counterexample · at ${at}` : "Counterexample"));
    const values = el("span", "evidence-values");
    values.append(
      el("span", "", `line ${step.compared_to} = ${step.values[0]}`),
      el("span", "", `line ${step.line} = ${step.values[1]}`)
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
        ? `First mistake: line ${error.compared_to} → ${error.line}.`
        : `First mistake: line ${error.line}.`),
      el("span", "", error.compared_to ? "Everything above it checks out." : "Look at this line again.")
    );
  } else {
    words.append(
      el("strong", "", "No mistakes found."),
      el("span", "", "Every line follows from the one before it.")
    );
  }
  summary.append(badge, words);
  results.append(summary);

  const marked = card("report-card", report.mode === "equation" ? "Solving, step by step" : "Your working, marked");
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

async function check({ reveal = false } = {}) {
  if (!engineReady) return;
  checkedOnce = true;
  const text = currentText();
  checkedAsMath = !textMode;
  remember(text);
  const outcome = await run(
    "check",
    { text },
    { statusLine: status, button: checkButton, stopButton: $("stop-check"), label: "Checking…", pane: results }
  );
  if (outcome.ok) renderReport(outcome.result);
  else renderFailure(results, outcome.error);
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
  for (const dialog of [examplesSheet, aboutSheet]) {
    dialog.addEventListener("click", (event) => {
      // a tap on the backdrop, or on a close button
      if (event.target === dialog || event.target.closest("[data-close]")) closeSheet(dialog);
    });
  }
  $("open-about").addEventListener("click", () => openSheet(aboutSheet));
  $("open-solve-examples").addEventListener("click", () => openExamples("solve"));
  $("open-check-examples").addEventListener("click", () => openExamples("check"));
}

function exampleButton(name, lines, onPick) {
  const button = el("button", "example");
  button.type = "button";
  button.append(el("span", "example-name", name));
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
  $("examples-title").textContent = context === "solve" ? "Examples" : "Worked examples to check";

  if (context === "solve") {
    const groups = new Map();
    for (const example of solveExamples) {
      const group = example.group || "More";
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group).push(example);
    }
    for (const [group, list] of groups) {
      exampleList.append(el("h3", "example-group", group));
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
  const { method = null, reveal = false } =
    typeof options === "string" ? { method: options } : options || {};
  const variable = solveVariable;
  if (!engineReady) return;
  // one line is an equation; several lines are a system
  const text = solveSheet.getText();
  if (!text) {
    renderFailure(
      solved,
      "Type something first — an equation like x^2 - 5x + 6 = 0, or something to work out like 1/2 + 1/3."
    );
    return;
  }
  const outcome = await run(
    "solve",
    { text, method, variable },
    { statusLine: solveStatus, button: solveButton, stopButton: $("stop-solve"), label: "Solving…", pane: solved }
  );
  if (outcome.ok) renderSolved(outcome.result);
  else renderFailure(solved, outcome.error);
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
  liveAnswer.replaceChildren(el("span", "live-tag", "Answer"), math);
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
    answerCard.append(el("p", "eyebrow", "Several letters"));
    answerCard.append(
      el("p", "answer-question", "This equation has several letters. Which one do you want to solve for?"),
      letterChips(solution.letters, null, "Solve for")
    );
    return;
  }

  const found = solution.answers.length || solution.everything;
  const head = el("div", "answer-head");
  head.append(el("p", "eyebrow solved-kind", solution.kind_label));
  if (found) {
    const verified = el("span", "answer-badge", "Checked");
    verified.prepend(icon("shield"));
    verified.title = "Every answer is checked in the original problem before it is shown";
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
    renderMath(intervals, String.raw`\text{that is } ` + solution.interval_latex);
    answerCard.append(intervals);
    if (solution.number_line.intervals.length || solution.number_line.points.length) {
      answerCard.append(numberLine(solution.number_line, renderMath));
    }
  }

  // the exact answer stays first; the decimal is what a calculator would say
  if (solution.decimal_latex) {
    const decimal = el("p", "answer-note answer-decimal");
    decimal.dataset.plain = "about " + solution.decimal;
    renderMath(decimal, solution.decimal_latex);
    answerCard.append(decimal);
  }

  // what the answer is only true for, such as x != -2 after cancelling (x + 2)
  if (solution.conditions && solution.conditions.length) {
    answerCard.append(el("p", "answer-note", "for " + solution.conditions.join(", ").replaceAll("!=", "≠")));
  }

  // a letter to solve for only makes sense for an equation
  if (solution.variable && solution.letters && solution.letters.length > 1) {
    answerCard.append(letterChips(solution.letters, solution.variable, "Solve for"));
  }

  if (solution.methods.length > 1) {
    const verb = solution.variable || solution.unknowns ? "Solve it by" : "Method";
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

  const steps = card("steps-card", "Steps");
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
    option.textContent = `${problem.section} · exercise ${problem.exercise}`;
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
  const section = card("practice-card", "Practice this skill");
  section.append(el("p", "card-intro", "Three more problems of the same kind, generated on your device."));
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
    const go = el("span", "practice-go", "Solve it");
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
  const section = card("graph-card", "Graph");
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
  targetLabel.textContent = calculus ? "Your expression" : "Your matrix";
  targetHelp.textContent = calculus ? EXPRESSION_HELP : MATRIX_HELP;
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
  summary.textContent = "Why?";
  summary.prepend(icon("bulb"));
  details.append(summary);

  const entries = [
    ["Rule", why.rule],
    ["Example", why.example],
    ["Common mistake", why.mistake],
  ];
  const panel = el("div", "why-panel");
  for (const [label, value] of entries) {
    const paragraph = el("p", "why-" + label.split(" ").at(-1).toLowerCase());
    const heading = el("strong", "", label);
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
  const reveal = el("button", "primary learning-button", "Reveal next step");
  reveal.type = "button";
  const tryNext = el("button", "tonal learning-button", "Try the next step");
  tryNext.type = "button";
  tryNext.prepend(icon("sparkle"));
  const showAll = el("button", "ghost-button learning-button", "Show all steps");
  showAll.type = "button";
  toolbar.append(reveal, tryNext, showAll);

  const rows = el("ol", "worked-steps");
  const elements = steps.map((step, index) => workedStep(step, index));
  elements.forEach((element) => rows.append(element));

  const tutor = el("form", "tutor-card");
  tutor.hidden = true;
  tutor.setAttribute("aria-label", "Try the next step yourself");
  const tutorLabel = el("label", "", "Write a valid next line");
  const tutorField = document.createElement("math-field");
  tutorField.setAttribute("aria-label", "Your next line");
  tutorLabel.append(tutorField);
  const tutorActions = el("div", "tutor-actions");
  const checkStep = el("button", "primary learning-button", "Check my step");
  checkStep.type = "submit";
  const cancelTutor = el("button", "ghost-button learning-button", "Cancel");
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
    progress.textContent = `Step ${Math.min(shown, steps.length)} of ${steps.length}`;
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
  }

  reveal.addEventListener("click", () => revealThrough(shown));
  showAll.addEventListener("click", () => revealThrough(steps.length - 1));
  tryNext.addEventListener("click", () => {
    tutorTarget = nextMathIndex();
    if (tutorTarget < 0) return;
    tutor.hidden = false;
    tutor.dataset.result = "";
    feedback.textContent = `Aim for step ${tutorTarget + 1}. Any mathematically valid next line counts.`;
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
      feedback.textContent = "Write a complete next line first.";
      return;
    }

    checkStep.disabled = true;
    feedback.textContent = "Checking your step…";
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
      feedback.textContent = `Yes — that step works.${note}`;
      revealThrough(tutorTarget);
      tutor.hidden = true;
      elements[tutorTarget].tabIndex = -1;
      elements[tutorTarget].focus();
      return;
    }
    const hint = checked.hints && checked.hints.length ? ` Hint: ${checked.hints[0]}` : "";
    tutor.dataset.result = "wrong";
    feedback.textContent = `${checked.message || "That line does not follow yet."}${hint}`;
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

async function showSteps({ reveal = false } = {}) {
  if (!engineReady) return;
  workedOnce = true;
  const operation = operationValue();
  const calculus = isCalculus(operation);
  const lower = operation === "integrate" ? lowerField.value.trim() : "";
  const upper = operation === "integrate" ? upperField.value.trim() : "";
  if (Boolean(lower) !== Boolean(upper)) {
    renderFailure(worked, "Fill in both limits for a definite integral, or leave both empty.");
    return;
  }
  const target = calculus ? expressionField.value : matrixInput.value;
  const outcome = await run(
    "steps",
    { operation, target, lower, upper },
    { statusLine: stepsStatus, button: stepsButton, stopButton: $("stop-steps"), label: "Working…", pane: worked }
  );
  if (outcome.ok) renderSolution(outcome.result);
  else renderFailure(worked, outcome.error);
  if (reveal) revealResults(worked);
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
  if (name === "check" && engineReady && !checkedOnce) check();
  if (name === "linalg" && engineReady && !workedOnce) showSteps();
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

function setUpTheme() {
  const current = document.documentElement.dataset.theme || "system";
  for (const input of document.querySelectorAll('input[name="theme"]')) {
    input.checked = input.value === current;
    input.addEventListener("change", () => applyTheme(input.value));
  }
  if (current !== "system") applyTheme(current);
}

// ---------------------------------------------------------------- start-up

async function boot() {
  setUpTabs();
  setUpSheets();
  setUpTheme();
  await customElements.whenDefined("math-field");

  for (const field of [expressionField, lowerField, upperField]) configureField(field);
  solveSheet = new MathSheet(equationLines, {
    onEnter: () => solve({ reveal: true }),
    // a new equation means the letter has to be chosen again
    onChange: () => {
      solveVariable = null;
      schedulePreview();
    },
    lineLabel: "An equation or expression",
  });
  $("add-equation").addEventListener("click", () => solveSheet.addLine());
  expressionField.value = String.raw`x^2\sin x`;

  sheet = new MathSheet(mathLines);
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
      if (engineReady) showSteps();
    });
  }
  updateOperationInput();

  const stop = () => engine.stop("Stopped. The engine restarts in the background.");
  $("stop-check").addEventListener("click", stop);
  $("stop-solve").addEventListener("click", stop);
  $("stop-steps").addEventListener("click", stop);

  // a shared link to someone's working opens on the Check tab
  if (sharedText()) selectTab("check");

  setEngineState("loading", "Loading");
  engine = new Engine({
    onStatus: (text) => {
      status.textContent = text;
      solveStatus.textContent = text;
      stepsStatus.textContent = text;
    },
  });
  const version = await engine.ready;
  engineReady = true;
  versionSlot.textContent = "mathlint " + version;
  setEngineState("ready", "Ready");
  enginePill.title = `mathlint ${version} runs on your device`;
  for (const line of [status, solveStatus, stepsStatus]) line.textContent = "";
  checkButton.disabled = false;
  stepsButton.disabled = false;
  solveButton.disabled = false;
  solve();
  if (activeTab() === "check") check();
}

boot().catch((error) => {
  setEngineState("error", "Offline");
  const message = "The math engine could not start.";
  for (const line of [status, solveStatus, stepsStatus]) line.textContent = message;
  for (const target of [solved, results]) {
    renderFailure(
      target,
      "Loading failed: " + error.message + ". Check your connection and reload — the engine comes from a CDN."
    );
  }
});
