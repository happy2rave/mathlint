// The recognized math, written onto the notebook's lines as if by hand: each
// line is uncovered left to right behind a soft pen point, one after another.
// Nothing is typeset again; a mask sweeps across the math already on the page,
// so it costs almost nothing, and it covers most of the recognizer's wait.
// With reduced motion the math simply appears.

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ``fields``: the lines' math fields, top to bottom.
export async function writeLines(fields) {
  if (reduced() || !fields.length || !Element.prototype.animate) return;
  // every line starts hidden, so the later ones do not show while the first is written
  for (const field of fields) field.style.clipPath = "inset(0 100% 0 0)";
  try {
    for (const field of fields) await writeOne(field);
  } finally {
    for (const field of fields) field.style.clipPath = "";
  }
}

async function writeOne(field) {
  const row = field.closest("li") ?? field.parentElement;
  const box = field.getBoundingClientRect();
  // the pen goes as far as the math, not to the end of the line
  const math = field.shadowRoot?.querySelector(".ML__latex")?.getBoundingClientRect();
  const start = math ? Math.max(0, math.left - box.left) : 0;
  const width = math ? math.width : box.width;
  const duration = Math.min(1400, Math.max(380, width * 3));
  const easing = "cubic-bezier(0.35, 0.1, 0.3, 1)";
  const pen = document.createElement("span");
  pen.className = "pen-trace";
  pen.setAttribute("aria-hidden", "true");
  pen.style.left = `${field.offsetLeft + start}px`;
  row.append(pen);
  field.style.clipPath = "";
  const uncover = field.animate(
    [
      { clipPath: `inset(0 ${box.width - start}px 0 0)` },
      { clipPath: `inset(0 ${Math.max(0, box.width - start - width)}px 0 0)` },
    ],
    { duration, easing }
  );
  pen.animate(
    [
      { transform: "translateX(0)", opacity: 0 },
      { opacity: 1, offset: 0.08 },
      { opacity: 1, offset: 0.9 },
      { transform: `translateX(${width}px)`, opacity: 0 },
    ],
    { duration, easing }
  );
  await uncover.finished.catch(() => {});
  pen.remove();
}
