// The math engine, off the main thread: Pyodide, SymPy and mathlint live here,
// so a slow problem can never freeze typing on the page.
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";

const status = (text) => postMessage({ type: "status", text });

const booting = (async () => {
  status("engine.status.loading");
  const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
  await pyodide.loadPackage(["sympy", "micropip"]);
  const info = await fetch("wheel.json").then((response) => response.json());
  await pyodide.pyimport("micropip").install(new URL(info.wheel, self.location.href).href);
  const handle = pyodide.runPython("from mathlint.web_api import handle\nhandle");
  postMessage({ type: "ready", version: JSON.parse(handle("version", "{}")).result });
  return handle;
})();

booting.catch((error) => postMessage({ type: "failed", error: String(error) }));

self.onmessage = async (event) => {
  const { id, kind, payload } = event.data;
  try {
    const handle = await booting;
    postMessage({ id, ...JSON.parse(handle(kind, JSON.stringify(payload))) });
  } catch (error) {
    postMessage({ id, ok: false, error: String(error) });
  }
};
