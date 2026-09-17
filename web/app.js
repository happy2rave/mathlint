import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";
import { EXAMPLES } from "./examples.js";

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const STORAGE_KEY = "mathlint:last-solution";

const solution = document.getElementById("solution");
const gutter = document.getElementById("gutter");
const status = document.getElementById("status");
const checkButton = document.getElementById("check");
const results = document.getElementById("results");
const examplesSelect = document.getElementById("examples");
const versionSlot = document.getElementById("version");

const MARKS = { OK: "✓", WRONG: "✗", WARNING: "!", UNSURE: "?" };

let runCheck = null;

function drawGutter() {
  const count = Math.max(solution.value.split("\n").length, 6);
  gutter.textContent = Array.from({ length: count }, (_, i) => i + 1).join("\n");
  gutter.scrollTop = solution.scrollTop;
}

function fillExamples() {
  EXAMPLES.forEach((example, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = example.name;
    examplesSelect.append(option);
  });
  examplesSelect.addEventListener("change", () => {
    const example = EXAMPLES[Number(examplesSelect.value)];
    if (!example) return;
    solution.value = example.text;
    drawGutter();
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
  return EXAMPLES[0].text;
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
  raw.textContent = step.raw;
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

function renderFailure(message) {
  results.replaceChildren();
  const box = document.createElement("div");
  box.className = "failure";
  const text = document.createElement("p");
  text.textContent = message;
  box.append(text);
  results.append(box);
}

function check() {
  if (!runCheck) return;
  const text = solution.value;
  remember(text);
  status.textContent = "Checking…";
  checkButton.disabled = true;
  // let the browser paint the status before SymPy takes the thread
  setTimeout(() => {
    try {
      const outcome = JSON.parse(runCheck(text));
      if (outcome.ok) renderReport(outcome.report);
      else renderFailure(outcome.error);
      status.textContent = "Ready";
    } catch (error) {
      renderFailure("Something went wrong while checking: " + error);
      status.textContent = "Ready";
    } finally {
      checkButton.disabled = false;
    }
  }, 16);
}

async function boot() {
  fillExamples();
  solution.value = initialText();
  drawGutter();
  solution.addEventListener("input", drawGutter);
  solution.addEventListener("scroll", () => (gutter.scrollTop = solution.scrollTop));
  solution.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") check();
  });
  checkButton.addEventListener("click", check);

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

  versionSlot.textContent = "mathlint " + pyodide.runPython("import mathlint; mathlint.__version__");
  status.textContent = "Ready";
  checkButton.disabled = false;
  check();
}

boot().catch((error) => {
  status.textContent = "The math engine could not start.";
  renderFailure(
    "Loading failed: " + error + ". Check your connection and reload — the engine comes from a CDN."
  );
});
