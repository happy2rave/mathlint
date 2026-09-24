// The handwriting pad: one ruled line to write on with a finger, a stylus or
// the mouse. The strokes are shown on a canvas as they are written, and drawn
// again, the same way every time, into the plain grayscale image the
// recognizer reads (rasterize).

// the pen's width, in CSS pixels, on the screen and in the recognizer's image
export const PEN = 3.2;

export class Strokes {
  constructor() {
    this.list = [];
  }

  get empty() {
    return this.list.length === 0;
  }

  begin(x, y) {
    this.list.push([[x, y]]);
  }

  // a point closer than a pixel to the last adds nothing
  extend(x, y) {
    const stroke = this.list[this.list.length - 1];
    if (!stroke) return;
    const [px, py] = stroke[stroke.length - 1];
    if (Math.hypot(x - px, y - py) >= 0.75) stroke.push([x, y]);
  }

  undo() {
    this.list.pop();
  }

  clear() {
    this.list = [];
  }
}

// The strokes as ink on white paper: each pixel as dark as the pen covers it.
export function rasterize(strokes, width, height, pen = PEN) {
  const gray = new Uint8Array(width * height).fill(255);
  const radius = pen / 2;
  for (const stroke of strokes) {
    for (let i = 0; i < stroke.length; i++) {
      const [ax, ay] = stroke[Math.max(0, i - 1)];
      const [bx, by] = stroke[i];
      const left = Math.max(0, Math.floor(Math.min(ax, bx) - radius - 1));
      const right = Math.min(width - 1, Math.ceil(Math.max(ax, bx) + radius + 1));
      const top = Math.max(0, Math.floor(Math.min(ay, by) - radius - 1));
      const bottom = Math.min(height - 1, Math.ceil(Math.max(ay, by) + radius + 1));
      const dx = bx - ax;
      const dy = by - ay;
      const length = dx * dx + dy * dy;
      for (let y = top; y <= bottom; y++) {
        for (let x = left; x <= right; x++) {
          const px = x + 0.5;
          const py = y + 0.5;
          const along = length ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / length)) : 0;
          const distance = Math.hypot(px - (ax + along * dx), py - (ay + along * dy));
          const cover = Math.max(0, Math.min(1, radius + 0.5 - distance));
          if (!cover) continue;
          const value = Math.round(255 * (1 - cover));
          if (value < gray[y * width + x]) gray[y * width + x] = value;
        }
      }
    }
  }
  return gray;
}

// The pad on the page: a canvas that follows the pointer.
export class Pad {
  constructor(canvas, { onStroke = () => {} } = {}) {
    this.canvas = canvas;
    this.strokes = new Strokes();
    this.onStroke = onStroke;
    this.drawing = null;
    canvas.addEventListener("pointerdown", (event) => this.#down(event));
    canvas.addEventListener("pointermove", (event) => this.#move(event));
    canvas.addEventListener("pointerup", (event) => this.#up(event));
    canvas.addEventListener("pointercancel", (event) => this.#up(event));
    new ResizeObserver(() => this.#fit()).observe(canvas);
  }

  get empty() {
    return this.strokes.empty;
  }

  #point(event) {
    const box = this.canvas.getBoundingClientRect();
    return [event.clientX - box.left, event.clientY - box.top];
  }

  #down(event) {
    if (event.button !== 0 || this.drawing !== null) return;
    event.preventDefault();
    this.canvas.setPointerCapture(event.pointerId);
    this.drawing = event.pointerId;
    this.strokes.begin(...this.#point(event));
    this.draw();
  }

  #move(event) {
    if (event.pointerId !== this.drawing) return;
    // every point the pointer passed through, not only the last one
    const points = event.getCoalescedEvents ? event.getCoalescedEvents() : [event];
    for (const point of points.length ? points : [event]) this.strokes.extend(...this.#point(point));
    this.draw();
  }

  #up(event) {
    if (event.pointerId !== this.drawing) return;
    this.drawing = null;
    this.onStroke();
  }

  #fit() {
    const ratio = window.devicePixelRatio || 1;
    const { width, height } = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.round(width * ratio);
    this.canvas.height = Math.round(height * ratio);
    this.draw();
  }

  draw() {
    const context = this.canvas.getContext("2d");
    const ratio = this.canvas.width / (this.canvas.getBoundingClientRect().width || 1);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    context.strokeStyle = context.fillStyle = getComputedStyle(this.canvas).color;
    context.lineWidth = PEN;
    context.lineCap = "round";
    context.lineJoin = "round";
    for (const stroke of this.strokes.list) {
      context.beginPath();
      context.moveTo(...stroke[0]);
      if (stroke.length === 1) context.lineTo(stroke[0][0] + 0.01, stroke[0][1]);
      for (const point of stroke.slice(1)) context.lineTo(...point);
      context.stroke();
    }
  }

  undo() {
    this.strokes.undo();
    this.draw();
    this.onStroke();
  }

  clear() {
    this.strokes.clear();
    this.draw();
    this.onStroke();
  }

  // What was written, as the recognizer's input: { gray, width, height }.
  image() {
    const { width, height } = this.canvas.getBoundingClientRect();
    const w = Math.max(1, Math.round(width));
    const h = Math.max(1, Math.round(height));
    return { gray: rasterize(this.strokes.list, w, h), width: w, height: h };
  }
}
