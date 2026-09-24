// The recognizer's own thread: the page never freezes while it reads.
//
// Messages in: { id, type: "load", url } and { id, type: "read", rgba | gray,
// width, height }. Messages out: "progress" while the model downloads,
// "loaded", "read" with every reading best first, or "error".

import { parseModel } from "./model.js";
import { beamSearch, toLatex } from "./decode.js";
import { prepare, toGray } from "./preprocess.js";

let model = null;

self.addEventListener("message", async ({ data }) => {
  const { id, type } = data;
  try {
    if (type === "load") {
      if (!model) model = parseModel(await download(data.url, id));
      self.postMessage({ id, type: "loaded" });
    } else if (type === "read") {
      if (!model) throw new Error("the recognizer is not loaded");
      const started = performance.now();
      const gray = data.gray ?? toGray(data.rgba, data.width, data.height);
      const ready = prepare(gray, data.width, data.height);
      const memory = model.encode(ready.pixels, ready.width);
      const readings = beamSearch(model, memory, { width: 4 }).map((reading) => ({
        latex: toLatex(model, reading.ids),
        tokens: reading.ids.map((token, index) => ({
          token: model.tokens[token],
          prob: reading.probs[index],
        })),
        score: reading.score,
      }));
      self.postMessage({ id, type: "read", readings, ms: performance.now() - started });
    }
  } catch (error) {
    self.postMessage({ id, type: "error", message: String(error?.message ?? error) });
  }
});

async function download(url, id) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`the recognizer could not be downloaded (${response.status})`);
  const total = Number(response.headers.get("content-length")) || 0;
  if (!response.body) return response.arrayBuffer();
  const reader = response.body.getReader();
  const chunks = [];
  let loaded = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    loaded += value.length;
    self.postMessage({ id, type: "progress", loaded, total });
  }
  const bytes = new Uint8Array(loaded);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.length;
  }
  return bytes.buffer;
}
