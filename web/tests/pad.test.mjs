import { test } from "node:test";
import assert from "node:assert/strict";

import { PEN, Strokes, rasterize } from "../pad.js";

test("a stroke is ink along its path and paper everywhere else", () => {
  const gray = rasterize([[[10, 20], [50, 20]]], 64, 40);
  const at = (x, y) => gray[y * 64 + x];
  for (let x = 10; x <= 50; x += 5) assert.equal(at(x, 19), 0, `on the line at ${x}`);
  assert.equal(at(30, 5), 255);
  assert.equal(at(60, 19), 255);
  // as wide as the pen, and softened at the edge
  const across = [15, 16, 17, 18, 19, 20, 21, 22, 23].map((y) => at(30, y));
  const inked = across.filter((value) => value < 128).length;
  assert.ok(Math.abs(inked - PEN) <= 1.5, `${inked} rows of ink`);
  assert.ok(across.some((value) => value > 0 && value < 255), "an edge in between");
});

test("a tap is a dot", () => {
  const gray = rasterize([[[20, 20]]], 40, 40);
  assert.equal(gray[19 * 40 + 19], 0);
  assert.equal(gray[19 * 40 + 30], 255);
});

test("the same strokes always make the same image", () => {
  const strokes = [[[3, 4], [30.5, 12.25], [41, 30]], [[8, 30]]];
  assert.deepEqual(rasterize(strokes, 48, 36), rasterize(strokes, 48, 36));
});

test("undo takes back the last stroke, clear takes them all", () => {
  const strokes = new Strokes();
  strokes.begin(1, 1);
  strokes.extend(1.2, 1.1); // closer than a pixel: nothing new
  strokes.extend(5, 5);
  strokes.begin(9, 9);
  assert.deepEqual(strokes.list, [[[1, 1], [5, 5]], [[9, 9]]]);
  strokes.undo();
  assert.deepEqual(strokes.list, [[[1, 1], [5, 5]]]);
  strokes.clear();
  assert.ok(strokes.empty);
});
