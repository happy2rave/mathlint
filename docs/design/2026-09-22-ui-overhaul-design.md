# v0.10.1 "A new look" — design

Date: 2026-09-22
Status: shipped in v0.10.1

## Goal

Redesign the web page as an app, with the phone as the main screen, ahead of
the v1.0 Android and iOS builds from the same code. Keep the notebook, where a
problem is written one line at a time on ruled paper with a red margin. Replace
everything around it.

## What stays

- The notebook: `MathSheet` in `editor.js`, one MathLive field per ruled line,
  numbered in a margin. Enter starts a new line on Check, and solves on Solve.
- The engine (`engine.js`, `worker.js`, `web_api.py`) and every request the page
  makes. The redesign changes no Python and no request shape.
- The keypad's keys (`keypad.js`), the graph and the number line.

## The shell

```
phone (< 900px)                      wide screen (>= 900px)
+---------------------------+        +------+------------------------------+
| mathlint          ● Ready |        | logo |                      ● Ready |
+---------------------------+        +------+--------------+---------------+
| Solve                     |        | Solve| notebook     | answer card   |
| [ notebook ]              |        | Check| [Solve ->]   | graph card    |
| [ Solve -> ]              |        | Work | keypad       | steps card    |
| answer / graph / steps    |        |      | (sticky)     | practice card |
+---------------------------+        | About|              |               |
| Solve  Check  Work  About |        +------+--------------+---------------+
+---------------------------+
```

- **Tabs:** a bottom bar on a phone, a rail on a wide screen. It is one
  `role="tablist"` with arrow-key movement. About is a button that opens a sheet,
  not a tab.
- **Keypad:** on a phone it is `position: fixed` at the bottom and rises while a
  math field has focus (`body.keypad-open`). The bottom bar hides while it is up.
  A tap on the keypad's background keeps the focus. The hide key blurs the
  field. On a wide screen it sits under the notebook. Its Enter key is labelled
  for the field it acts on: Solve, Check (tutor), Go (Work out), or ↵ (a new
  line on Check).
- **Sheets:** `<dialog>` elements. They are bottom sheets on a phone and centred
  dialogs on a wide screen. Examples (grouped by `group` in
  `solve-examples.json`, drawn with KaTeX) and the open-textbook library share
  one sheet. About holds the privacy note, the source link, the version, the
  theme picker and the support link.
- **Theme:** tokens on `:root`, redefined for dark under
  `prefers-color-scheme` unless `data-theme="light"`, and again under
  `data-theme="dark"`. The choice is kept in `localStorage` (`mathlint:theme`)
  and applied by an inline script before the first paint.
- **Safe areas:** `viewport-fit=cover`, with `env(safe-area-inset-*)` padding on
  the top bar, the bottom bar, the keypad and the sheets. This is what a
  Capacitor build needs.

## Results as cards

- **Answer:** the problem's kind, a "Checked" badge when there is an answer, the
  answer on a tinted panel, interval notation and the number line, the decimal,
  conditions, and the letter and method chips.
- **Graph:** zoom and reset buttons float over the plot.
- **Steps:** a progress bar, a numbered timeline, a **Why?** pill that opens the
  rule, example and common mistake, and the tutor's attempt written on a
  notebook line.
- **Practice:** problems drawn as math. They are a swipeable row on a phone and
  a grid on a wide screen.
- **Check:** a verdict card first, then the marked lines. The same marks are
  drawn on the notebook's margin line: `MathSheet.setMarks()` sets
  `data-mark` on each filled line, and typing on a line clears its mark.

## Pitfalls found on the way

- KaTeX's hidden MathML copy is absolutely positioned. Inside a sideways
  scroller (the practice row) it escaped the scroller and widened the page, and
  phones zoomed the whole app out. `.katex { position: relative; }` contains it.
- A tutor field must be on the page before `configureField` runs, so a steps
  card is attached first and filled after.

## Tests

`tests/test_v0101_web.py` checks the source for the notebook, the phone
viewport and safe areas, the docked keypad, the margin marks, both themes, the
KaTeX containment, the example groups, that every icon used is defined, and
that every page file is stamped by `build_web.py`.
