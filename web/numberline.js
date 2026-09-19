// The answer of an inequality on a number line: shaded intervals, filled
// circles for ends that belong to the answer, open circles for ends that do
// not, and arrows for intervals that go on forever.

const SVG = "http://www.w3.org/2000/svg";
const WIDTH = 600;
const HEIGHT = 56;
const AXIS_Y = 24;
const MARGIN = 28;

function svg(tag, attributes) {
  const element = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
  return element;
}

// The numbers the picture has to show, with room around them.
function range(data) {
  const values = [];
  for (const interval of data.intervals) {
    if (interval.from !== null) values.push(interval.from);
    if (interval.to !== null) values.push(interval.to);
  }
  for (const point of data.points) values.push(point.at);
  if (!values.length) return [-5, 5];
  const low = Math.min(...values);
  const high = Math.max(...values);
  const pad = Math.max(1, (high - low) * 0.35);
  return [Math.floor(low - pad), Math.ceil(high + pad)];
}

function tickStep(span) {
  for (const step of [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]) {
    if (span / step <= 12) return step;
  }
  return Math.pow(10, Math.ceil(Math.log10(span / 10)));
}

// `renderMath(element, latex)` typesets the labels of the ends.
export function numberLine(data, renderMath) {
  const [low, high] = range(data);
  const x = (value) => MARGIN + ((value - low) / (high - low)) * (WIDTH - 2 * MARGIN);

  const figure = document.createElement("figure");
  figure.className = "number-line";
  const picture = svg("svg", {
    viewBox: `0 0 ${WIDTH} ${HEIGHT}`,
    role: "img",
    "aria-hidden": "true",
  });
  figure.append(picture);

  // the axis, with an arrow at each end
  picture.append(
    svg("line", { x1: 6, y1: AXIS_Y, x2: WIDTH - 6, y2: AXIS_Y, class: "axis" }),
    svg("path", { d: `M ${WIDTH - 12} ${AXIS_Y - 5} L ${WIDTH - 4} ${AXIS_Y} L ${WIDTH - 12} ${AXIS_Y + 5}`, class: "axis" }),
    svg("path", { d: `M 12 ${AXIS_Y - 5} L 4 ${AXIS_Y} L 12 ${AXIS_Y + 5}`, class: "axis" })
  );

  const ends = new Set();
  for (const interval of data.intervals) {
    if (interval.from !== null) ends.add(interval.from);
    if (interval.to !== null) ends.add(interval.to);
  }
  for (const point of data.points) ends.add(point.at);

  // whole-number ticks, left out where an end's own label goes
  const step = tickStep(high - low);
  for (let value = Math.ceil(low / step) * step; value <= high; value += step) {
    picture.append(svg("line", { x1: x(value), y1: AXIS_Y - 4, x2: x(value), y2: AXIS_Y + 4, class: "tick" }));
    const crowded = [...ends].some((end) => Math.abs(x(end) - x(value)) < 18);
    if (!crowded) {
      const label = svg("text", { x: x(value), y: AXIS_Y + 22, class: "tick-label" });
      label.textContent = String(value);
      picture.append(label);
    }
  }

  // the answer, drawn over the axis
  for (const interval of data.intervals) {
    const start = interval.from === null ? 6 : x(interval.from);
    const end = interval.to === null ? WIDTH - 6 : x(interval.to);
    picture.append(svg("line", { x1: start, y1: AXIS_Y, x2: end, y2: AXIS_Y, class: "answer-band" }));
    if (interval.from === null) {
      picture.append(svg("path", { d: `M 14 ${AXIS_Y - 7} L 3 ${AXIS_Y} L 14 ${AXIS_Y + 7}`, class: "answer-arrow" }));
    }
    if (interval.to === null) {
      picture.append(svg("path", { d: `M ${WIDTH - 14} ${AXIS_Y - 7} L ${WIDTH - 3} ${AXIS_Y} L ${WIDTH - 14} ${AXIS_Y + 7}`, class: "answer-arrow" }));
    }
  }

  const labels = document.createElement("div");
  labels.className = "number-line-labels";
  figure.append(labels);
  const mark = (value, closed, latex) => {
    picture.append(svg("circle", { cx: x(value), cy: AXIS_Y, r: 6, class: closed ? "end closed" : "end open" }));
    const label = document.createElement("span");
    label.style.left = `${(x(value) / WIDTH) * 100}%`;
    label.dataset.plain = String(value);
    renderMath(label, latex);
    labels.append(label);
  };
  for (const interval of data.intervals) {
    if (interval.from !== null) mark(interval.from, interval.from_closed, interval.from_label);
    if (interval.to !== null) mark(interval.to, interval.to_closed, interval.to_label);
  }
  for (const point of data.points) mark(point.at, true, point.label);
  return figure;
}
