// A graph under the answer: the curves, the answer's points, the shaded part
// of the x-axis for an inequality. Drag to move, scroll or pinch to zoom; the
// buttons do the same without a pointer. Moving asks the engine for fresh
// points across the new range.

const SVG = "http://www.w3.org/2000/svg";
const WIDTH = 640;
const HEIGHT = 360;
const REFETCH_MS = 160;

function svg(tag, attributes = {}) {
  const element = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
  return element;
}

// Grid lines at 1, 2 or 5 times a power of ten, about eight across.
function ticks(low, high) {
  const rough = (high - low) / 8;
  const power = Math.pow(10, Math.floor(Math.log10(rough)));
  const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough) || power * 10;
  const values = [];
  for (let value = Math.ceil(low / step) * step; value <= high + step * 1e-9; value += step) {
    values.push(Math.abs(value) < step * 1e-9 ? 0 : value);
  }
  return values;
}

function format(value) {
  return Number.parseFloat(value.toPrecision(6)).toString();
}

export class Graph {
  constructor(spec, { fetchSamples, renderMath }) {
    this.spec = spec;
    this.fetchSamples = fetchSamples;
    this.home = { ...spec.view };
    this.view = { ...spec.view };
    this.samples = spec.samples;
    this.round = 0;
    this.pointers = new Map();

    this.element = document.createElement("figure");
    this.element.className = "graph";
    this.picture = svg("svg", {
      viewBox: `0 0 ${WIDTH} ${HEIGHT}`,
      role: "img",
      tabindex: "0",
      "aria-label": "Graph. Drag to move, scroll or pinch to zoom; arrow keys move, + and - zoom.",
    });
    const stage = document.createElement("div");
    stage.className = "graph-stage";
    stage.append(this.picture, this.#controls());
    this.element.append(stage, this.#legend(renderMath));
    this.#listen();
    this.draw();
  }

  #controls() {
    const bar = document.createElement("div");
    bar.className = "graph-controls";
    const button = (label, text, action) => {
      const control = document.createElement("button");
      control.type = "button";
      control.className = "graph-button";
      control.textContent = text;
      control.setAttribute("aria-label", label);
      control.addEventListener("click", action);
      bar.append(control);
    };
    button("Zoom in", "+", () => this.zoom(1 / 1.5));
    button("Zoom out", "−", () => this.zoom(1.5));
    button("Back to the start", "⟲", () => this.reset());
    return bar;
  }

  #legend(renderMath) {
    const legend = document.createElement("figcaption");
    legend.className = "graph-legend";
    this.spec.curves.forEach((curve, index) => {
      const item = document.createElement("span");
      item.className = `legend-item curve-${index % 4}`;
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      const math = document.createElement("span");
      math.dataset.plain = curve.expr;
      renderMath(math, curve.latex);
      item.append(swatch, math);
      legend.append(item);
    });
    if (this.spec.area) {
      const item = document.createElement("span");
      item.className = "legend-item area-note";
      item.textContent = "Shaded: the area, counted positive above the x-axis and negative below";
      legend.append(item);
    }
    for (const line of this.spec.vertical) {
      const item = document.createElement("span");
      item.className = "legend-item vertical";
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      const math = document.createElement("span");
      renderMath(math, line.latex);
      item.append(swatch, math);
      legend.append(item);
    }
    return legend;
  }

  // data coordinates -> picture coordinates
  sx(x) {
    return ((x - this.view.x_min) / (this.view.x_max - this.view.x_min)) * WIDTH;
  }

  sy(y) {
    return HEIGHT - ((y - this.view.y_min) / (this.view.y_max - this.view.y_min)) * HEIGHT;
  }

  draw() {
    const { x_min, x_max, y_min, y_max } = this.view;
    const layers = [];

    // what the answer covers, for an inequality
    for (const band of this.spec.shade) {
      const from = band.from === null ? x_min : band.from;
      const to = band.to === null ? x_max : band.to;
      const left = this.sx(Math.max(from, x_min));
      const right = this.sx(Math.min(to, x_max));
      if (right - left > 0.5) {
        layers.push(svg("rect", { x: left, y: 0, width: right - left, height: HEIGHT, class: "shade" }));
      }
    }

    for (const value of ticks(x_min, x_max)) {
      const at = this.sx(value);
      layers.push(svg("line", { x1: at, y1: 0, x2: at, y2: HEIGHT, class: value === 0 ? "axis" : "grid" }));
      if (value !== 0) layers.push(this.#label(format(value), at, Math.min(Math.max(this.sy(0) + 16, 14), HEIGHT - 4), "middle"));
    }
    for (const value of ticks(y_min, y_max)) {
      const at = this.sy(value);
      layers.push(svg("line", { x1: 0, y1: at, x2: WIDTH, y2: at, class: value === 0 ? "axis" : "grid" }));
      if (value !== 0) layers.push(this.#label(format(value), Math.min(Math.max(this.sx(0) - 6, 34), WIDTH - 4), at + 4, "end"));
    }

    // a definite integral: the area between the curve and the x-axis
    if (this.spec.area && this.samples.curves.length) {
      for (const [side, clamp] of [["above", Math.max], ["below", Math.min]]) {
        layers.push(svg("path", { d: this.#area(this.spec.area, clamp), class: `area area-${side}` }));
      }
    }

    this.samples.curves.forEach((ys, index) => {
      layers.push(svg("path", { d: this.#path(this.samples.xs, ys), class: `curve curve-${index % 4}` }));
    });
    for (const line of this.spec.vertical) {
      const at = this.sx(line.x);
      layers.push(svg("line", { x1: at, y1: 0, x2: at, y2: HEIGHT, class: "curve vertical" }));
    }

    for (const mark of this.spec.marks) {
      const x = this.sx(mark.x);
      const y = this.sy(mark.y);
      if (x < -10 || x > WIDTH + 10 || y < -10 || y > HEIGHT + 10) continue;
      layers.push(svg("circle", { cx: x, cy: y, r: 5, class: mark.closed ? "mark closed" : "mark open" }));
      layers.push(this.#label(mark.label, x + 8, y - 8, "start", "mark-label"));
    }
    this.picture.replaceChildren(...layers);
  }

  // The region between the first curve and the axis from `from` to `to`, on one
  // side of the axis only (clamp is Math.max for above, Math.min for below).
  #area({ from, to }, clamp) {
    const { xs } = this.samples;
    const ys = this.samples.curves[0];
    const points = [];
    for (let index = 0; index < xs.length; index++) {
      if (xs[index] < from || xs[index] > to || ys[index] === null) continue;
      points.push([xs[index], clamp(ys[index], 0)]);
    }
    if (points.length < 2) return "M0 0";
    let d = `M${this.sx(points[0][0]).toFixed(1)} ${this.sy(0).toFixed(1)} `;
    for (const [x, y] of points) d += `L${this.sx(x).toFixed(1)} ${this.sy(y).toFixed(1)} `;
    d += `L${this.sx(points.at(-1)[0]).toFixed(1)} ${this.sy(0).toFixed(1)} Z`;
    return d;
  }

  #label(text, x, y, anchor, className = "tick-label") {
    const label = svg("text", { x, y, "text-anchor": anchor, class: className });
    label.textContent = text;
    return label;
  }

  // One path per curve, broken where it is not defined or jumps off the page
  // (an asymptote would otherwise be drawn as a steep line).
  #path(xs, ys) {
    let d = "";
    let pen = false;
    let lastY = null;
    for (let index = 0; index < xs.length; index++) {
      const y = ys[index];
      if (y === null || y === undefined) {
        pen = false;
        continue;
      }
      const px = this.sx(xs[index]);
      const py = this.sy(y);
      const jump = lastY !== null && Math.abs(py - lastY) > HEIGHT * 2;
      if (Math.abs(py) > HEIGHT * 50) {
        pen = false;
        lastY = null;
        continue;
      }
      d += `${pen && !jump ? "L" : "M"}${px.toFixed(1)} ${py.toFixed(1)} `;
      pen = true;
      lastY = py;
    }
    return d || "M0 0";
  }

  // --- moving and zooming ---------------------------------------------------------

  pan(dx, dy) {
    const width = this.view.x_max - this.view.x_min;
    const height = this.view.y_max - this.view.y_min;
    const shiftX = (-dx / WIDTH) * width;
    const shiftY = (dy / HEIGHT) * height;
    this.view.x_min += shiftX;
    this.view.x_max += shiftX;
    this.view.y_min += shiftY;
    this.view.y_max += shiftY;
    this.changed();
  }

  zoom(factor, cx = WIDTH / 2, cy = HEIGHT / 2) {
    const x = this.view.x_min + (cx / WIDTH) * (this.view.x_max - this.view.x_min);
    const y = this.view.y_max - (cy / HEIGHT) * (this.view.y_max - this.view.y_min);
    this.view.x_min = x + (this.view.x_min - x) * factor;
    this.view.x_max = x + (this.view.x_max - x) * factor;
    this.view.y_min = y + (this.view.y_min - y) * factor;
    this.view.y_max = y + (this.view.y_max - y) * factor;
    this.changed();
  }

  reset() {
    this.view = { ...this.home };
    this.changed();
  }

  changed() {
    this.draw();
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.refetch(), REFETCH_MS);
  }

  async refetch() {
    if (!this.spec.curves.length) return;
    const round = ++this.round;
    const { x_min, x_max } = this.view;
    const width = x_max - x_min;
    // a little beyond each side, so a small drag has points ready
    const samples = await this.fetchSamples(x_min - width * 0.25, x_max + width * 0.25);
    if (round !== this.round || !samples) return;
    this.samples = samples;
    this.draw();
  }

  #toPicture(event) {
    const box = this.picture.getBoundingClientRect();
    return [((event.clientX - box.left) / box.width) * WIDTH, ((event.clientY - box.top) / box.height) * HEIGHT];
  }

  #listen() {
    const picture = this.picture;
    picture.addEventListener("pointerdown", (event) => {
      picture.setPointerCapture(event.pointerId);
      this.pointers.set(event.pointerId, this.#toPicture(event));
    });
    picture.addEventListener("pointermove", (event) => {
      if (!this.pointers.has(event.pointerId)) return;
      const now = this.#toPicture(event);
      if (this.pointers.size === 1) {
        const [x0, y0] = this.pointers.get(event.pointerId);
        this.pointers.set(event.pointerId, now);
        this.pan(now[0] - x0, now[1] - y0);
        return;
      }
      // two fingers: zoom by how much their distance changed
      const [first, second] = [...this.pointers.values()];
      const before = Math.hypot(first[0] - second[0], first[1] - second[1]);
      this.pointers.set(event.pointerId, now);
      const [a, b] = [...this.pointers.values()];
      const after = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (before > 0 && after > 0) this.zoom(before / after, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2);
    });
    const release = (event) => this.pointers.delete(event.pointerId);
    picture.addEventListener("pointerup", release);
    picture.addEventListener("pointercancel", release);
    picture.addEventListener(
      "wheel",
      (event) => {
        event.preventDefault();
        const [x, y] = this.#toPicture(event);
        this.zoom(event.deltaY > 0 ? 1.15 : 1 / 1.15, x, y);
      },
      { passive: false }
    );
    picture.addEventListener("keydown", (event) => {
      const moves = { ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40] };
      if (moves[event.key]) {
        event.preventDefault();
        this.pan(...moves[event.key]);
      } else if (event.key === "+" || event.key === "=") {
        this.zoom(1 / 1.5);
      } else if (event.key === "-") {
        this.zoom(1.5);
      } else if (event.key === "0") {
        this.reset();
      }
    });
  }
}
