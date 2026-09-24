import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

import { parseModel } from "../recognizer/model.js";
import { beamSearch, toLatex } from "../recognizer/decode.js";

const fixtures = new URL("./fixtures/", import.meta.url);

function load(url) {
  const bytes = readFileSync(url);
  return parseModel(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
}

function pixels(image) {
  return new Uint8Array(Buffer.from(image.pixels, "base64"));
}

function closeTo(actual, expected, tolerance, what) {
  assert.equal(actual.length, expected.length, `${what}: length`);
  let worst = 0;
  for (let i = 0; i < expected.length; i++) worst = Math.max(worst, Math.abs(actual[i] - expected[i]));
  assert.ok(worst < tolerance, `${what}: off by ${worst}`);
}

test("the tiny model's memory and logits match PyTorch's", () => {
  const model = load(new URL("tiny.bin", fixtures));
  const expected = JSON.parse(readFileSync(new URL("tiny.json", fixtures), "utf8"));
  const memory = model.encode(pixels(expected.image), expected.image.width);
  assert.equal(memory.cells, expected.memoryShape[0]);
  closeTo(memory.values, expected.memory, 1e-3, "memory");

  const context = model.begin(memory);
  const vocabulary = model.tokens.length;
  let past = null;
  expected.tokens.forEach((token, position) => {
    const step = model.step(context, past, token, position);
    past = step.past;
    const row = expected.logits.slice(position * vocabulary, (position + 1) * vocabulary);
    closeTo(step.logits, row, 1e-3, `logits at ${position}`);
  });
});

const real = new URL("../recognizer/recognizer.bin", import.meta.url);
const readings = new URL("readings.json", fixtures);

test("the real model reads the fixture images as Python does", { skip: !existsSync(real) || !existsSync(readings) }, () => {
  const model = load(real);
  for (const reading of JSON.parse(readFileSync(readings, "utf8"))) {
    const memory = model.encode(pixels(reading.image), reading.image.width);
    const [best] = beamSearch(model, memory, { width: 4 });
    assert.equal(toLatex(model, best.ids), reading.python, reading.kind);
    assert.equal(best.probs.length, best.ids.length);
  }
});
