import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { HEIGHT, prepare, roundEven, toGray } from "../recognizer/preprocess.js";

const cases = JSON.parse(readFileSync(new URL("./fixtures/prepare.json", import.meta.url), "utf8"));

const bytes = (image) => new Uint8Array(Buffer.from(image.pixels, "base64"));

// the same page export.synthetic_page() draws
function syntheticPage(width, height) {
  const page = new Uint8Array(width * height);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const writing =
        (Math.floor(x / 23) + Math.floor(y / 31)) % 3 === 0 &&
        y > Math.floor(height / 3) && y < Math.floor((2 * height) / 3) &&
        x > Math.floor(width / 8) && x < Math.floor((7 * width) / 8);
      page[y * width + x] = writing ? 30 : 150 + ((x * 7 + y * 13) % 60) + Math.floor((x * 40) / width);
    }
  }
  return page;
}

for (const example of cases) {
  test(`${example.name} is prepared exactly as in training`, () => {
    const [width, height] = example.synthetic ?? [example.input.width, example.input.height];
    const gray = example.synthetic ? syntheticPage(width, height) : bytes(example.input);
    const ready = prepare(gray, width, height);
    const expected = bytes(example.expected);
    assert.equal(ready.width, example.expected.width);
    assert.equal(ready.pixels.length, HEIGHT * ready.width);
    let differ = 0;
    let worst = 0;
    for (let i = 0; i < expected.length; i++) {
      const gap = Math.abs(ready.pixels[i] - expected[i]);
      if (gap) differ++;
      worst = Math.max(worst, gap);
    }
    // the same numbers, but for a rare half rounded the other way
    assert.ok(worst <= 1, `off by ${worst}`);
    assert.ok(differ <= expected.length * 0.001, `${differ} pixels differ`);
  });
}

test("halves round to even, as in Python", () => {
  assert.deepEqual([0.5, 1.5, 2.5, -0.5, 2.4, 2.6].map(roundEven), [0, 2, 2, 0, 2, 3]);
});

test("colour becomes gray as Pillow makes it", () => {
  const rgba = new Uint8Array([255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 10, 20, 30, 255]);
  assert.deepEqual([...toGray(rgba, 4, 1)], [76, 150, 29, 18]);
});
