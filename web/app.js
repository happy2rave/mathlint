import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";
import { MathSheet, configureField, displayLatex } from "./editor.js";
import { Keypad } from "./keypad.js";

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
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

const MARKS = { OK: "✓", WRONG: "✗", WARNING: "!", UNSURE: "?" };
const EXPRESSION_HELP =
  "Tap the keys or type it: x^2 sin x, e^(2x), 1/(x^2+1). The variable is picked up from the expression.";
const MATRIX_HELP =
  "Write it as [[2, 1], [3, 4]], MATLAB style [2 1; 3 4], or as a LaTeX pmatrix. " +
  "Fractions stay exact — no decimals.";

let runCheck = null;
let runSteps = null;
let examples = [];
let sheet = null;
let textMode = false;
let lastField = null;
let checkedAsMath = true;

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
    if (runCheck) check();
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

function onCheckTab() {
  return $("tab-check").getAttribute("aria-selected") === "true";
}

function keypadTarget() {
  const active = document.activeElement;
  if (active && active.tagName === "MATH-FIELD" && isVisible(active)) return active;
  if (isVisible(lastField)) return lastField;
  return onCheckTab() ? sheet.fields.at(-1) : expressionField;
}

function handleEnter(field) {
  if (sheet.contains(field)) sheet.newLineAfter(field);
  else showSteps();
}

// ---------------------------------------------------------------- results

function renderMath(target, latex) {
  if (!latex || !window.katex) {
    target.textContent = target.dataset.plain || "";
    return;
  }
  try {
    window.katex.render(latex, target, { throwOnError: false, displayMode: false });
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

function check() {
  if (!runCheck) return;
  const text = currentText();
  checkedAsMath = !textMode;
  remember(text);
  status.textContent = "Checking…";
  checkButton.disabled = true;
  // let the browser paint the status before SymPy takes the thread
  setTimeout(() => {
    try {
      const outcome = JSON.parse(runCheck(text));
      if (outcome.ok) renderReport(outcome.report);
      else renderFailure(results, outcome.error);
    } catch (error) {
      renderFailure(results, "Something went wrong while checking: " + error);
    } finally {
      status.textContent = "Ready";
      checkButton.disabled = false;
    }
  }, 16);
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

function showSteps() {
  if (!runSteps) return;
  const operation = operationSelect.value;
  const calculus = isCalculus(operation);
  const lower = operation === "integrate" ? lowerField.value.trim() : "";
  const upper = operation === "integrate" ? upperField.value.trim() : "";
  if (Boolean(lower) !== Boolean(upper)) {
    renderFailure(worked, "Fill in both limits for a definite integral, or leave both empty.");
    return;
  }
  const target = calculus ? expressionField.value : matrixInput.value;

  stepsStatus.textContent = "Working…";
  stepsButton.disabled = true;
  setTimeout(() => {
    try {
      const outcome = JSON.parse(runSteps(operation, target, lower, upper));
      if (outcome.ok) renderSolution(outcome.solution);
      else renderFailure(worked, outcome.error);
    } catch (error) {
      renderFailure(worked, "Something went wrong: " + error);
    } finally {
      stepsStatus.textContent = "";
      stepsButton.disabled = false;
    }
  }, 16);
}

// ---------------------------------------------------------------- start-up

function setUpTabs() {
  const tabs = [
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
    });
  }
  $("panel-linalg").hidden = true;
}

async function boot() {
  setUpTabs();
  await customElements.whenDefined("math-field");

  for (const field of [expressionField, lowerField, upperField]) configureField(field);
  expressionField.value = String.raw`x^2\sin x`;

  sheet = new MathSheet(mathLines);
  new Keypad(keypadRoot, { getTarget: keypadTarget, onEnter: handleEnter });
  checkKeypadSlot.append(keypadRoot);

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
        if (onCheckTab()) check();
        else showSteps();
      }
    },
    true
  );

  examples = await fetch("examples.json").then((response) => response.json());
  fillExamples();
  setText(initialText());

  modeToggle.addEventListener("click", () => setTextMode(!textMode));
  solutionText.addEventListener("input", drawGutter);
  solutionText.addEventListener("scroll", () => (gutter.scrollTop = solutionText.scrollTop));
  checkButton.addEventListener("click", check);
  stepsButton.addEventListener("click", showSteps);
  operationSelect.addEventListener("change", () => {
    updateOperationInput();
    if (runSteps) showSteps();
  });
  updateOperationInput();

  status.textContent = "Loading the math engine (about 12 MB, once)…";
  const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
  await pyodide.loadPackage(["sympy", "micropip"]);

  const wheelInfo = await fetch("wheel.json").then((response) => response.json());
  const micropip = pyodide.pyimport("micropip");
  await micropip.install(new URL(wheelInfo.wheel, location.href).href);

  runCheck = pyodide.runPython(`
import json
import mathlint

def _run(text):
    try:
        return json.dumps({"ok": True, "report": mathlint.check(text).to_dict()})
    except mathlint.MathlintError as error:
        return json.dumps({"ok": False, "error": str(error)})
    except Exception as error:  # never leave the page without an explanation
        return json.dumps({"ok": False, "error": f"{type(error).__name__}: {error}"})

_run
`);

  runSteps = pyodide.runPython(`
import json
import sympy
from mathlint.parse.plain import parse_expression
from mathlint.steps import (
    differentiate_solution,
    integrate_solution,
    parse_matrix,
    solve_linalg,
)

def _variable(expression):
    symbols = sorted(expression.free_symbols, key=lambda symbol: symbol.name)
    return symbols[0] if len(symbols) == 1 else sympy.Symbol("x")

def _steps(operation, text, lower, upper):
    try:
        if operation in ("diff", "integrate"):
            expression = parse_expression(text).expr
            variable = _variable(expression)
            if operation == "diff":
                solution = differentiate_solution(expression, variable)
            else:
                solution = integrate_solution(
                    expression,
                    variable,
                    lower=parse_expression(lower).expr if lower.strip() else None,
                    upper=parse_expression(upper).expr if upper.strip() else None,
                )
        else:
            solution = solve_linalg(operation, parse_matrix(text))
        return json.dumps({"ok": True, "solution": solution.to_dict()})
    except mathlint.MathlintError as error:
        return json.dumps({"ok": False, "error": str(error)})
    except Exception as error:
        return json.dumps({"ok": False, "error": f"{type(error).__name__}: {error}"})

_steps
`);

  versionSlot.textContent = "mathlint " + pyodide.runPython("import mathlint; mathlint.__version__");
  status.textContent = "Ready";
  checkButton.disabled = false;
  stepsButton.disabled = false;
  check();
}

boot().catch((error) => {
  status.textContent = "The math engine could not start.";
  renderFailure(
    results,
    "Loading failed: " + error + ". Check your connection and reload — the engine comes from a CDN."
  );
});
