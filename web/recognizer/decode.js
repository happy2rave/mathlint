// Reading a line: beam search, as training/mathrec/beam.py does it.
//
// The ``width`` likeliest partial readings are kept at every step; every
// finished one comes back, best first, each token with its probability. The
// notebook then takes the first reading it can read, and names the symbols it
// was unsure of (under UNSURE).

import { logSoftmax } from "./layers.js";

export const UNSURE = 0.6;
const LIMIT = 120;

function penalty(length) {
  return ((5 + length) / 6) ** 0.6;
}

function topK(values, k) {
  const order = Array.from(values.keys());
  order.sort((a, b) => values[b] - values[a]);
  return order.slice(0, k);
}

export function beamSearch(model, memory, { width = 4, limit = LIMIT } = {}) {
  const { start, end } = model.special;
  const context = model.begin(memory);
  // a reading so far: its tokens, their probabilities, log probability, and
  // the self-attention state that produced its last logits
  let alive = [{ ids: [start], probs: [], total: 0, past: null, logits: null }];
  const finished = [];
  for (let step = 0; step < limit - 1; step++) {
    const candidates = [];
    for (const reading of alive) {
      const position = reading.ids.length - 1;
      const { logits, past } = model.step(context, reading.past, reading.ids[position], position);
      const logProbs = logSoftmax(logits);
      for (const index of topK(logProbs, width)) {
        candidates.push({
          ids: [...reading.ids, index],
          probs: [...reading.probs, Math.exp(logProbs[index])],
          total: reading.total + logProbs[index],
          past,
        });
      }
    }
    candidates.sort((a, b) => b.total / penalty(b.ids.length - 1) - a.total / penalty(a.ids.length - 1));
    alive = [];
    for (const candidate of candidates) {
      if (candidate.ids[candidate.ids.length - 1] === end) {
        finished.push({
          ids: candidate.ids.slice(1, -1),
          probs: candidate.probs.slice(0, -1),
          score: candidate.total / penalty(candidate.ids.length - 1),
        });
      } else {
        alive.push(candidate);
      }
      if (alive.length === width) break;
    }
    const bestAlive = Math.max(-Infinity, ...alive.map((r) => r.total / penalty(r.ids.length - 1)));
    if (finished.length >= width && Math.max(...finished.map((r) => r.score)) >= bestAlive) break;
    if (!alive.length) break;
  }
  finished.sort((a, b) => b.score - a.score);
  return finished;
}

// Token ids back to LaTeX: a space only where a command would swallow a letter.
export function toLatex(model, ids) {
  let text = "";
  for (const id of ids) {
    const token = model.tokens[id];
    if (text && /\\[A-Za-z]+$/.test(text) && /^[A-Za-z]/.test(token)) text += " ";
    text += token;
  }
  return text;
}
