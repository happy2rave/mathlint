// A photo, or the pad, turned into what the model reads: 96 px tall, ink dark.
//
// This is training/mathrec/image.py's prepare(), step for step and number for
// number (a test holds the two together), because the model learned from
// images prepared that way: shrink big photos, even out the light, stretch the
// contrast, find the ink while ignoring ruled lines and specks at the edges,
// crop with a margin of paper, and scale.

export const HEIGHT = 96;
export const MAX_WIDTH = 768;
export const MIN_WIDTH = 32;
const WORKING_HEIGHT = 384;
const PAPER = 250;
const DARK = 128;
const TRIM = 0.003;
const RULED = 0.5;
const MARGIN = 0.08;

// Python's round() and numpy's rint: halves go to the even neighbour.
export function roundEven(x) {
  const floor = Math.floor(x);
  const diff = x - floor;
  if (diff > 0.5) return floor + 1;
  if (diff < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}

const clip = (x) => (x < 0 ? 0 : x > 255 ? 255 : x);

// RGBA (from a canvas) to grayscale, as Pillow's convert("L") does it.
export function toGray(rgba, width, height) {
  const gray = new Uint8Array(width * height);
  for (let i = 0, j = 0; i < gray.length; i++, j += 4) {
    gray[i] = (rgba[j] * 19595 + rgba[j + 1] * 38470 + rgba[j + 2] * 7471 + 0x8000) >> 16;
  }
  return gray;
}

// The largest (or smallest) value within ``radius``, edges repeated.
function extreme(pixels, width, height, radius, larger) {
  const pick = larger ? Math.max : Math.min;
  const across = new Float64Array(width * height);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let best = pixels[y * width + x];
      for (let d = -radius; d <= radius; d++) {
        const yy = Math.min(height - 1, Math.max(0, y + d));
        best = pick(best, pixels[yy * width + x]);
      }
      across[y * width + x] = best;
    }
  }
  const out = new Float64Array(width * height);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let best = across[y * width + x];
      for (let d = -radius; d <= radius; d++) {
        const xx = Math.min(width - 1, Math.max(0, x + d));
        best = pick(best, across[y * width + xx]);
      }
      out[y * width + x] = best;
    }
  }
  return out;
}

// The mean within ``radius``, edges repeated: running sums, rows then columns,
// added in the same order as numpy's cumsum so the numbers come out the same.
function boxBlur(pixels, width, height, radius) {
  const size = 2 * radius + 1;
  const down = new Float64Array(width * height);
  const sums = new Float64Array(height + size);
  for (let x = 0; x < width; x++) {
    let total = 0;
    for (let i = 0; i < height + size; i++) {
      const y = Math.min(height - 1, Math.max(0, i - radius - 1));
      total += pixels[y * width + x];
      sums[i] = total;
    }
    for (let y = 0; y < height; y++) down[y * width + x] = (sums[y + size] - sums[y]) / size;
  }
  const out = new Float64Array(width * height);
  const row = new Float64Array(width + size);
  for (let y = 0; y < height; y++) {
    let total = 0;
    for (let i = 0; i < width + size; i++) {
      const x = Math.min(width - 1, Math.max(0, i - radius - 1));
      total += down[y * width + x];
      row[i] = total;
    }
    for (let x = 0; x < width; x++) out[y * width + x] = (row[x + size] - row[x]) / size;
  }
  return out;
}

function inkSpan(counts, trim) {
  let total = 0;
  for (const count of counts) total += count;
  if (total === 0) return null;
  const skip = total * trim;
  let cumulative = 0;
  let start = -1;
  let end = -1;
  for (let i = 0; i < counts.length; i++) {
    cumulative += counts[i];
    if (start < 0 && cumulative > skip) start = i;
    if (end < 0 && cumulative >= total - skip) end = i + 1;
  }
  return [start, Math.max(end, start + 1)];
}

// For each output pixel, the input pixels it reads and their weights.
function taps(sizeIn, sizeOut) {
  const scale = sizeIn / sizeOut;
  const support = Math.max(scale, 1);
  const count = Math.ceil(2 * support) + 2;
  const index = new Int32Array(sizeOut * count);
  const weights = new Float64Array(sizeOut * count);
  for (let o = 0; o < sizeOut; o++) {
    const centre = (o + 0.5) * scale;
    const first = Math.floor(centre - support);
    let total = 0;
    for (let t = 0; t < count; t++) {
      const i = first + t;
      let w = Math.max(0, 1 - Math.abs(i + 0.5 - centre) / support);
      if (i < 0 || i >= sizeIn) w = 0;
      weights[o * count + t] = w;
      index[o * count + t] = Math.min(sizeIn - 1, Math.max(0, i));
      total += w;
    }
    for (let t = 0; t < count; t++) weights[o * count + t] /= total;
  }
  return { index, weights, count };
}

export function resize(pixels, width, height, newWidth, newHeight) {
  let data = Float64Array.from(pixels);
  let w = width;
  let h = height;
  if (newHeight !== h) {
    const { index, weights, count } = taps(h, newHeight);
    const out = new Float64Array(newHeight * w);
    for (let o = 0; o < newHeight; o++) {
      for (let x = 0; x < w; x++) {
        let sum = 0;
        for (let t = 0; t < count; t++) sum += data[index[o * count + t] * w + x] * weights[o * count + t];
        out[o * w + x] = sum;
      }
    }
    data = out;
    h = newHeight;
  }
  if (newWidth !== w) {
    const { index, weights, count } = taps(w, newWidth);
    const out = new Float64Array(h * newWidth);
    for (let y = 0; y < h; y++) {
      for (let o = 0; o < newWidth; o++) {
        let sum = 0;
        for (let t = 0; t < count; t++) sum += data[y * w + index[o * count + t]] * weights[o * count + t];
        out[y * newWidth + o] = sum;
      }
    }
    data = out;
    w = newWidth;
  }
  return Uint8Array.from(data, (v) => clip(roundEven(v)));
}

// Steps 1–3: shrink big photos, even out the light, stretch the contrast.
function normalize(gray, width, height) {
  let pixels = gray;
  // 1. shrink by a whole factor, averaging blocks
  const factor = Math.ceil(height / WORKING_HEIGHT);
  if (factor > 1) {
    const h = Math.floor(height / factor);
    const w = Math.floor(width / factor);
    const small = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        let sum = 0;
        for (let dy = 0; dy < factor; dy++) {
          for (let dx = 0; dx < factor; dx++) sum += gray[(y * factor + dy) * width + x * factor + dx];
        }
        small[y * w + x] = roundEven(sum / (factor * factor));
      }
    }
    pixels = small;
    width = w;
    height = h;
  }
  // 2. even out the light
  const radius = Math.max(1, Math.floor(height / 16));
  const closed = extreme(extreme(pixels, width, height, radius, true), width, height, radius, false);
  const paper = boxBlur(closed, width, height, Math.max(1, Math.floor(radius / 2)));
  let even = new Uint8Array(width * height);
  for (let i = 0; i < even.length; i++) {
    even[i] = clip(roundEven((pixels[i] * 255) / Math.max(paper[i], 1)));
  }
  // 3. stretch the contrast
  const histogram = new Array(256).fill(0);
  for (const value of even) histogram[value]++;
  let darkest = 0;
  for (let cumulative = 0; darkest < 256; darkest++) {
    cumulative += histogram[darkest];
    if (cumulative >= even.length * 0.01) break;
  }
  if (darkest < PAPER) {
    even = Uint8Array.from(even, (v) => clip(roundEven(((v - darkest) * 255) / (PAPER - darkest))));
  }
  return { even, width, height, factor };
}

// Step 4: the ink, without ruled lines; with how much of it each row and column has.
function inkOf(even, width, height) {
  const ink = new Uint8Array(width * height);
  for (let i = 0; i < ink.length; i++) ink[i] = even[i] < DARK ? 1 : 0;
  for (let y = 0; y < height; y++) {
    let count = 0;
    for (let x = 0; x < width; x++) count += ink[y * width + x];
    if (count / width > RULED) ink.fill(0, y * width, (y + 1) * width);
  }
  for (let x = 0; x < width; x++) {
    let count = 0;
    for (let y = 0; y < height; y++) count += ink[y * width + x];
    if (count / height > RULED) for (let y = 0; y < height; y++) ink[y * width + x] = 0;
  }
  const rows = new Array(height).fill(0);
  const columns = new Array(width).fill(0);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      rows[y] += ink[y * width + x];
      columns[x] += ink[y * width + x];
    }
  }
  return { rows, columns };
}

// Grayscale pixels (any size) → { pixels, width }, 96 rows, ready to read.
export function prepare(gray, width, height) {
  const normal = normalize(gray, width, height);
  ({ width, height } = normal);
  const { even } = normal;
  // 4. find the ink, ignoring ruled lines and specks
  const counts = inkOf(even, width, height);
  const rows = inkSpan(counts.rows, TRIM);
  const columns = inkSpan(counts.columns, TRIM);
  if (!rows || !columns) return { pixels: new Uint8Array(HEIGHT * MIN_WIDTH).fill(255), width: MIN_WIDTH };
  const [top, bottom] = rows;
  const [left, right] = columns;
  // 5. crop with a margin of paper (white past the photo's edges), and scale
  const pad = Math.max(2, roundEven((bottom - top) * MARGIN));
  const cropW = right - left + 2 * pad;
  const cropH = bottom - top + 2 * pad;
  const crop = new Uint8Array(cropW * cropH).fill(255);
  for (let y = 0; y < cropH; y++) {
    const sy = top - pad + y;
    if (sy < 0 || sy >= height) continue;
    for (let x = 0; x < cropW; x++) {
      const sx = left - pad + x;
      if (sx >= 0 && sx < width) crop[y * cropW + x] = even[sy * width + sx];
    }
  }
  return fitted(crop, cropW, cropH);
}

// The lines of writing in a photo, top to bottom, as [top, bottom) rows of
// ``gray``. Bands of ink with paper between them are lines; a band close
// enough to the next (a fraction's numerator, its bar, its denominator) is
// the same line. Specks too small to be writing are left out.
export function splitLines(gray, width, height) {
  const normal = normalize(gray, width, height);
  const { rows } = inkOf(normal.even, normal.width, normal.height);
  const blank = Math.max(1, normal.width * 0.002);
  let bands = [];
  let start = -1;
  rows.forEach((count, y) => {
    if (count > blank && start < 0) start = y;
    if (count <= blank && start >= 0) {
      bands.push([start, y]);
      start = -1;
    }
  });
  if (start >= 0) bands.push([start, rows.length]);
  if (bands.length <= 1) return [[0, height]];
  const heights = bands.map(([a, b]) => b - a).sort((a, b) => a - b);
  const typical = heights[Math.floor(heights.length / 2)];
  const merged = [bands[0]];
  for (const band of bands.slice(1)) {
    const last = merged[merged.length - 1];
    if (band[0] - last[1] < 0.35 * typical) last[1] = band[1];
    else merged.push([...band]);
  }
  bands = merged.filter(([a, b]) => b - a >= 0.3 * typical);
  if (bands.length <= 1) return [[0, height]];
  // halfway through the paper between lines, back in the photo's own rows
  return bands.map(([a, b], i) => {
    const above = i === 0 ? 0 : Math.floor((bands[i - 1][1] + a) / 2);
    const below = i === bands.length - 1 ? normal.height : Math.ceil((b + bands[i + 1][0]) / 2);
    return [above * normal.factor, Math.min(height, below * normal.factor)];
  });
}

function fitted(crop, width, height) {
  let scale = HEIGHT / height;
  if (width * scale > MAX_WIDTH) scale = MAX_WIDTH / width;
  const newWidth = Math.max(MIN_WIDTH, roundEven(width * scale));
  const newHeight = Math.max(1, Math.min(HEIGHT, roundEven(height * scale)));
  const resized = resize(crop, width, height, newWidth, newHeight);
  if (newHeight === HEIGHT) return { pixels: resized, width: newWidth };
  const out = new Uint8Array(HEIGHT * newWidth).fill(255);
  out.set(resized, Math.floor((HEIGHT - newHeight) / 2) * newWidth);
  return { pixels: out, width: newWidth };
}
