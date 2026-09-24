// The math engine, off the main thread: Pyodide, SymPy and mathlint live here,
// so a slow problem can never freeze typing on the page. Every file comes from
// this site (scripts/vendor.py), so the engine works offline once cached.
import { loadPyodide } from "./vendor/pyodide-314.0.7/pyodide.mjs";

const PYODIDE_URL = new URL("vendor/pyodide-314.0.7/", self.location.href).href;

const status = (text) => postMessage({ type: "status", text });

const booting = (async () => {
  status("engine.status.loading");
  // mathlint's wheel downloads while Python starts
  const wheel = fetch("wheel.json")
    .then((response) => response.json())
    .then((info) => fetch(info.wheel))
    .then((response) => response.arrayBuffer());
  const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
  const [, archive] = await Promise.all([pyodide.loadPackage(["sympy"]), wheel]);
  // a wheel is a zip of the package: unpacking it installs it, no micropip needed
  pyodide.unpackArchive(archive, "wheel");
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
