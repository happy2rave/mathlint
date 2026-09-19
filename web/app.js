import { MathSheet, configureField, displayLatex } from "./editor.js";
import { Engine } from "./engine.js";
import { Keypad } from "./keypad.js";

const STORAGE_KEY = "mathlint:last-solution";

const $ = (id) => document.getElementById(id);
const status = $("status");
const checkButton = $("check");
const results = $("results");
const examplesSelect = $("examples");
const versionSlot = $("version");
const mathLines = $("math-lines");
const textSheet = $("text-sheet");
const solutionText = $("solution");
const gutter = $("gutter");
const modeToggle = $("mode-toggle");
const checkKeypadSlot = $("keypad-slot-check");
const stepsKeypadSlot = $("keypad-slot-steps");
const keypadRoot = $("keypad");
const operationSelect = $("operation");
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
const solveExamplesSelect = $("solve-examples");

const MARKS = { OK: "✓", WRONG: "✗", WARNING: "!", UNSURE: "?" };
const EXPRESSION_HELP =
  "Tap the keys or type it: x^2 sin x, e^(2x), 1/(x^2+1). The variable is picked up from the expression.";
const MATRIX_HELP =
  "Write it as [[2, 1], [3, 4]], MATLAB style [2 1; 3 4], or as a LaTeX pmatrix. " +
  "Fractions stay exact — no decimals.";

let engine = null;
let engineReady = false;
let examples = [];
let sheet = null;
let solveSheet = null;
let solveVariable = null;
let previewTimer = null;
let previewRound = 0;
let textMode = false;
let lastField = null;
let checkedAsMath = true;
let checkedOnce = false;

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
  modeToggle.textContent = on ? "Use the math keypad" : "Type as text";
  modeToggle.setAttribute("aria-pressed", String(on));
  drawGutter();
  if (on) solutionText.focus();
  else sheet.fields[0]?.focus();
}

function fillExamples() {
  examples.forEach((example, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = example.name;
    examplesSelect.append(option);
  });
  examplesSelect.addEventListener("change", () => {
    const example = examples[Number(examplesSelect.value)];
    if (!example) return;
    setText(example.lines.join("\n"));
    if (engineReady) check();
  });
}

function initialText() {
  const hash = new URLSearchParams(location.hash.slice(1)).get("s");
  if (hash) return hash;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return saved;
  } catch {
    /* private browsing: fall through to the example */
  }
  return examples.length ? examples[0].lines.join("\n") : "";
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

function activeTab() {
  for (const name of ["solve", "check", "linalg"]) {
    if ($(`tab-${name}`).getAttribute("aria-selected") === "true") return name;
  }
  return "solve";
}

function keypadTarget() {
  const active = document.activeElement;
  if (active && active.tagName === "MATH-FIELD" && isVisible(active)) return active;
  if (isVisible(lastField)) return lastField;
  const tab = activeTab();
  if (tab === "solve") return solveSheet.active || solveSheet.fields[0];
  return tab === "check" ? sheet.fields.at(-1) : expressionField;
}

function handleEnter(field) {
  if (sheet.contains(field)) sheet.newLineAfter(field);
  else if (solveSheet.contains(field)) solve();
  else showSteps();
}

// ---------------------------------------------------------------- results

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

function stepElement(step) {
  const row = document.createElement("div");
  const verdict = step.verdict || "";
  row.className = "verdict-line" + (verdict ? ` mark-${verdict.toLowerCase()}` : "");

  const mark = document.createElement("div");
  mark.className = "mark";
  mark.innerHTML = `${step.line} <b>${MARKS[verdict] || ""}</b>`;
  row.append(mark);

  const body = document.createElement("div");

  const raw = document.createElement("div");
  raw.className = "step-raw";
  raw.dataset.plain = step.raw;
  if (checkedAsMath) {
    raw.classList.add("as-math");
    renderMath(raw, displayLatex(step.raw));
  } else {
    raw.textContent = step.raw;
  }
  body.append(raw);

  const read = document.createElement("p");
  read.className = "step-read";
  const label = document.createElement("span");
  label.textContent = "reads as ";
  const math = document.createElement("span");
  math.dataset.plain = step.read_as;
  renderMath(math, step.read_as_latex);
  read.append(label, math);
  body.append(read);

  if (step.message) {
    const note = document.createElement("p");
    note.className = "step-note " + verdict.toLowerCase();
    const method = { exact: " (proved exactly)", numeric: " (checked with numbers)" }[step.method] || "";
    note.textContent = step.message + method;
    body.append(note);
  }

  if (step.values && step.compared_to) {
    const evidence = document.createElement("p");
    evidence.className = "evidence";
    const at = step.counterexample
      ? Object.entries(step.counterexample).map(([name, value]) => `${name} = ${value}`).join(", ")
      : null;
    evidence.textContent =
      (at ? `at ${at}:  ` : "") +
      `line ${step.compared_to} = ${step.values[0]},  line ${step.line} = ${step.values[1]}`;
    body.append(evidence);
  }

  for (const hint of step.hints || []) {
    const element = document.createElement("p");
    element.className = "hint";
    element.textContent = hint;
    body.append(element);
  }

  for (const warning of step.warnings || []) {
    const element = document.createElement("p");
    element.className = "warn";
    element.textContent = warning;
    body.append(element);
  }

  row.append(body);
  return row;
}

function renderReport(report) {
  results.replaceChildren();

  const heading = document.createElement("h2");
  heading.textContent = report.mode === "equation" ? "Solving, step by step" : "Your working, marked";
  results.append(heading);

  for (const step of report.steps) results.append(stepElement(step));

  const summary = document.createElement("p");
  const error = report.steps.find((step) => step.verdict === "WRONG");
  if (error) {
    summary.className = "summary broken";
    summary.innerHTML = error.compared_to
      ? `<strong>First mistake: line ${error.compared_to} → ${error.line}.</strong> Everything above it checks out.`
      : `<strong>First mistake: line ${error.line}.</strong>`;
  } else {
    summary.className = "summary clean";
    summary.innerHTML = "<strong>No mistakes found.</strong> Every line follows from the one before it.";
  }
  results.append(summary);

  for (const note of report.notes || []) {
    const element = document.createElement("p");
    element.className = "warn";
    element.textContent = note;
    results.append(element);
  }
}

function renderFailure(target, message) {
  target.replaceChildren();
  const box = document.createElement("div");
  box.className = "failure";
  const text = document.createElement("p");
  text.textContent = message;
  box.append(text);
  target.append(box);
}

// Run one engine request while showing a status and a Stop button.
async function run(kind, payload, { statusLine, button, stopButton, label }) {
  statusLine.textContent = label;
  button.disabled = true;
  stopButton.hidden = false;
  try {
    return await engine.call(kind, payload);
  } finally {
    statusLine.textContent = engineReady ? "Ready" : statusLine.textContent;
    button.disabled = false;
    stopButton.hidden = true;
  }
}

async function check() {
  if (!engineReady) return;
  checkedOnce = true;
  const text = currentText();
  checkedAsMath = !textMode;
  remember(text);
  const outcome = await run(
    "check",
    { text },
    { statusLine: status, button: checkButton, stopButton: $("stop-check"), label: "Checking…" }
  );
  if (outcome.ok) renderReport(outcome.result);
  else renderFailure(results, outcome.error);
}

// ---------------------------------------------------------------- solving

function fillSolveExamples(list) {
  list.forEach((example, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = example.name;
    solveExamplesSelect.append(option);
  });
  solveExamplesSelect.addEventListener("change", () => {
    const example = list[Number(solveExamplesSelect.value)];
    if (!example) return;
    solveSheet.setLines(example.lines);
    solveVariable = null;
    solve();
  });
}

async function solve(method = null) {
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
    { statusLine: solveStatus, button: solveButton, stopButton: $("stop-solve"), label: "Solving…" }
  );
  if (outcome.ok) renderSolved(outcome.result);
  else renderFailure(solved, outcome.error);
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
  renderMath(liveAnswer, latex);
  liveAnswer.hidden = false;
}

// Chips for the letter to solve for; the chosen one is pressed.
function letterChips(letters, current, label) {
  const chips = document.createElement("div");
  chips.className = "method-chips";
  chips.setAttribute("role", "group");
  chips.setAttribute("aria-label", label);
  const text = document.createElement("span");
  text.textContent = label;
  chips.append(text);
  for (const letter of letters) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = letter;
    chip.setAttribute("aria-pressed", String(letter === current));
    chip.addEventListener("click", () => {
      solveVariable = letter;
      solve();
    });
    chips.append(chip);
  }
  return chips;
}

function renderSolved(solution) {
  solved.replaceChildren();

  if (solution.needs_letter) {
    const question = document.createElement("p");
    question.className = "solved-kind";
    question.textContent = "This equation has several letters. Which one do you want to solve for?";
    solved.append(question, letterChips(solution.letters, null, "Solve for"));
    return;
  }

  const kind = document.createElement("p");
  kind.className = "solved-kind";
  kind.textContent = solution.kind_label;
  solved.append(kind);

  const answer = document.createElement("div");
  answer.className = "answer" + (solution.answers.length || solution.everything ? "" : " none");
  answer.dataset.plain = solution.answer_text;
  renderMath(answer, solution.answer_latex, true);
  solved.append(answer);

  // the exact answer stays first; the decimal is what a calculator would say
  if (solution.decimal_latex) {
    const decimal = document.createElement("p");
    decimal.className = "answer-note answer-decimal";
    decimal.dataset.plain = "about " + solution.decimal;
    renderMath(decimal, solution.decimal_latex);
    solved.append(decimal);
  }

  // what the answer is only true for, such as x != -2 after cancelling (x + 2)
  if (solution.conditions && solution.conditions.length) {
    const note = document.createElement("p");
    note.className = "answer-note";
    note.textContent = "for " + solution.conditions.join(", ").replaceAll("!=", "≠");
    solved.append(note);
  }

  // a letter to solve for only makes sense for an equation
  if (solution.variable && solution.letters && solution.letters.length > 1) {
    solved.append(letterChips(solution.letters, solution.variable, "Solve for"));
  }

  if (solution.methods.length > 1) {
    const verb = solution.variable || solution.unknowns ? "Solve it by" : "Method";
    const chips = document.createElement("div");
    chips.className = "method-chips";
    chips.setAttribute("role", "group");
    chips.setAttribute("aria-label", verb);
    const label = document.createElement("span");
    label.textContent = verb;
    chips.append(label);
    for (const method of solution.methods) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.textContent = method.label;
      chip.setAttribute("aria-pressed", String(method.id === solution.method));
      chip.addEventListener("click", () => solve(method.id));
      chips.append(chip);
    }
    solved.append(chips);
  }

  const heading = document.createElement("h2");
  heading.textContent = "Steps";
  solved.append(heading);
  solution.steps.forEach((step, index) => solved.append(workedStep(step, index)));
}

// ---------------------------------------------------------------- worked solutions

function isCalculus(operation) {
  return operation === "diff" || operation === "integrate";
}

function updateOperationInput() {
  const operation = operationSelect.value;
  const calculus = isCalculus(operation);
  expressionBlock.hidden = !calculus;
  matrixBlock.hidden = calculus;
  bounds.hidden = operation !== "integrate";
  stepsKeypadSlot.hidden = !calculus;
  targetLabel.textContent = calculus ? "Your expression" : "Your matrix";
  targetHelp.textContent = calculus ? EXPRESSION_HELP : MATRIX_HELP;
}

function workedStep(step, index) {
  const row = document.createElement("div");
  row.className = "worked-step";

  const number = document.createElement("div");
  number.className = "worked-index";
  number.textContent = String(index + 1);
  row.append(number);

  const body = document.createElement("div");
  const text = document.createElement("p");
  text.className = "worked-text";
  text.textContent = step.text;
  if (step.operation) {
    const operation = document.createElement("span");
    operation.className = "worked-operation";
    operation.textContent = "   " + step.operation;
    text.append(operation);
  }
  body.append(text);

  if (step.math_latex || step.math) {
    const math = document.createElement("div");
    math.className = "worked-math";
    math.dataset.plain = step.math;
    renderMath(math, step.math_latex);
    body.append(math);
  }

  row.append(body);
  return row;
}

function renderSolution(solution) {
  worked.replaceChildren();
  const heading = document.createElement("h2");
  heading.textContent = solution.title;
  worked.append(heading);
  solution.steps.forEach((step, index) => worked.append(workedStep(step, index)));
  if (solution.summary) {
    const summary = document.createElement("p");
    summary.className = "summary";
    summary.textContent = solution.summary;
    worked.append(summary);
  }
}

async function showSteps() {
  if (!engineReady) return;
  const operation = operationSelect.value;
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
    { statusLine: stepsStatus, button: stepsButton, stopButton: $("stop-steps"), label: "Working…" }
  );
  if (outcome.ok) renderSolution(outcome.result);
  else renderFailure(worked, outcome.error);
}

// ---------------------------------------------------------------- start-up

function setUpTabs() {
  const tabs = [
    { tab: $("tab-solve"), panels: ["panel-solve"], slot: solveKeypadSlot },
    { tab: $("tab-check"), panels: ["panel-check", "results"], slot: checkKeypadSlot },
    { tab: $("tab-linalg"), panels: ["panel-linalg"], slot: stepsKeypadSlot },
  ];
  for (const entry of tabs) {
    entry.tab.addEventListener("click", () => {
      for (const other of tabs) {
        const selected = other === entry;
        other.tab.setAttribute("aria-selected", String(selected));
        for (const id of other.panels) $(id).hidden = !selected;
      }
      entry.slot.append(keypadRoot);
      // the check tab runs its example the first time it is opened
      if (entry.tab.id === "tab-check" && engineReady && !checkedOnce) check();
    });
  }
  $("panel-linalg").hidden = true;
}

async function boot() {
  setUpTabs();
  await customElements.whenDefined("math-field");

  for (const field of [expressionField, lowerField, upperField]) configureField(field);
  solveSheet = new MathSheet(equationLines, {
    onEnter: () => solve(),
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
  new Keypad(keypadRoot, { getTarget: keypadTarget, onEnter: handleEnter });
  solveKeypadSlot.append(keypadRoot);

  document.addEventListener("focusin", (event) => {
    const field = event.composedPath().find((element) => element.tagName === "MATH-FIELD");
    if (field) lastField = field;
  });
  window.addEventListener(
    "keydown",
    (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        event.stopImmediatePropagation();
        const tab = activeTab();
        if (tab === "solve") solve();
        else if (tab === "check") check();
        else showSteps();
      }
    },
    true
  );

  const solveExamples = await fetch("solve-examples.json").then((response) => response.json());
  fillSolveExamples(solveExamples);
  solveSheet.setLines(solveExamples[0].lines);

  examples = await fetch("examples.json").then((response) => response.json());
  fillExamples();
  setText(initialText());

  modeToggle.addEventListener("click", () => setTextMode(!textMode));
  solutionText.addEventListener("input", drawGutter);
  solutionText.addEventListener("scroll", () => (gutter.scrollTop = solutionText.scrollTop));
  checkButton.addEventListener("click", check);
  solveButton.addEventListener("click", () => solve());
  stepsButton.addEventListener("click", showSteps);
  operationSelect.addEventListener("change", () => {
    updateOperationInput();
    if (engineReady) showSteps();
  });
  updateOperationInput();

  const stop = () => engine.stop("Stopped. The engine restarts in the background.");
  $("stop-check").addEventListener("click", stop);
  $("stop-solve").addEventListener("click", stop);
  $("stop-steps").addEventListener("click", stop);

  engine = new Engine({
    onStatus: (text) => {
      status.textContent = text;
      solveStatus.textContent = text;
    },
  });
  const version = await engine.ready;
  engineReady = true;
  versionSlot.textContent = "mathlint " + version;
  status.textContent = "Ready";
  solveStatus.textContent = "Ready";
  checkButton.disabled = false;
  stepsButton.disabled = false;
  solveButton.disabled = false;
  solve();
}

boot().catch((error) => {
  status.textContent = "The math engine could not start.";
  solveStatus.textContent = "The math engine could not start.";
  renderFailure(
    results,
    "Loading failed: " + error.message + ". Check your connection and reload — the engine comes from a CDN."
  );
});
