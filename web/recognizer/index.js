// Reading math from a photo or from the pad, for the rest of the app.
//
// The app imports this file only when the camera or the pad first opens; the
// model (about 4 MB) is downloaded then, once, and kept offline by the service
// worker from that moment on.
//
//   const reader = new Reader();
//   await reader.load((loaded, total) => ...);
//   const { lines } = await reader.read({ rgba, width, height, lines: true });
//   const { latex, unsure } = await choose(lines[0], firstReadable);

import { UNSURE } from "./decode.js";

export { UNSURE };

export class Reader {
  constructor(modelUrl = new URL("./recognizer.bin", import.meta.url)) {
    this.modelUrl = String(modelUrl);
    this.worker = null;
    this.waiting = new Map();
    this.next = 1;
    this.loading = null;
  }

  #send(message, onProgress) {
    if (!this.worker) {
      this.worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
      this.worker.addEventListener("message", ({ data }) => {
        const job = this.waiting.get(data.id);
        if (!job) return;
        if (data.type === "progress") return job.onProgress?.(data.loaded, data.total);
        this.waiting.delete(data.id);
        if (data.type === "error") job.reject(new Error(data.message));
        else job.resolve(data);
      });
    }
    const id = this.next++;
    return new Promise((resolve, reject) => {
      this.waiting.set(id, { resolve, reject, onProgress });
      this.worker.postMessage({ id, ...message });
    });
  }

  // Download (the first time) and set up the model; ``onProgress(loaded, total)``.
  load(onProgress) {
    this.loading ??= this.#send({ type: "load", url: this.modelUrl }, onProgress).catch((error) => {
      this.loading = null; // a failed download can be tried again
      throw error;
    });
    return this.loading;
  }

  // Every reading of every line of an image ({ rgba | gray, width, height,
  // lines }), best first: { lines: [[reading, ...], ...], ms }. Without
  // ``lines`` the whole image is one line (the pad).
  async read(image) {
    await this.load();
    return this.#send({ type: "read", ...image });
  }
}

// The likeliest reading the notebook can read, with the symbols the recognizer
// was unsure of. ``firstReadable(latexList)`` (maybe async) answers with the
// index of the first one it can read, or null; without it, or when none can be
// read, the likeliest reading is taken. Null when there is no reading at all.
export async function choose(readings, firstReadable = null) {
  if (!readings.length) return null;
  let index = 0;
  if (firstReadable) {
    const found = await firstReadable(readings.map((reading) => reading.latex));
    if (Number.isInteger(found)) index = found;
  }
  const chosen = readings[index];
  const unsure = chosen.tokens
    .map((entry, position) => ({ ...entry, position }))
    .filter((entry) => entry.prob < UNSURE);
  return { latex: chosen.latex, unsure, score: chosen.score };
}
