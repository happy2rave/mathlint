# Roadmap

**Goal:** a math app at Photomath's level of quality, with every premium feature
free, plus the thing Photomath does not do: check *your* working.

## Principles

1. **Everything free, for good.** The math runs on your own device, so there are
   no servers to pay for and nothing to charge for.
2. **It checks your working.** Not only "here is the answer", but "here is your
   first wrong step" — and, later, "try the next step yourself".
3. **Every answer is verified.** Answers are substituted back into the original
   problem. When mathlint cannot solve something it says so instead of guessing.
4. **Private and open.** Nothing you type or photograph leaves your device.

Every change lands as one focused commit with its tests. Every milestone ends in
a release with a changelog and an updated web page. A growing problem bank —
real problems with known answers — runs on every commit.

## Milestones

| Version | Theme | What you get |
|---|---|---|
| v0.1–v0.4 | Done | Mistake finder, linear algebra and calculus steps, math editor and keypad |
| **v0.5** | Solve it | Type an equation, get the answer and the steps |
| **v0.6** | Many unknowns | Systems of equations, and "solve this formula for y" |
| v0.7 | Calculator | Arithmetic and simplifying with steps, a live answer as you type |
| v0.8 | Inequalities and graphs | Sign charts, interval answers, interactive graphs, function analysis |
| v0.9 | Calculus, complete | Limits, implicit derivatives, harder integrals, differential equations |
| v0.10 | Premium, free | "Why?" on every step, step-by-step reveal, animated steps, tutor mode, practice |
| v0.11 | App quality | Installable, offline, history, speed, accessibility, translations |
| v1.0 | App stores | Android and iOS apps from the same code |
| v1.x | Camera | Photo to editable math, printed first, then handwriting — on the device |

### v0.5 — Solve it

- The math engine runs in a background worker, so the page never freezes, and
  a slow problem can be stopped.
- A problem classifier and a **Solve** tab: type an equation, get the answer
  first, then the steps.
- Linear equations: expand, clear fractions, collect terms, isolate, divide.
- Quadratics with a method switcher: factoring, the quadratic formula,
  completing the square, square roots.
- Higher-degree polynomials: common factors, substitution, rational roots and
  synthetic division.
- Rational equations: excluded values, clearing denominators, rejecting roots
  that divide by zero.
- Radical and absolute-value equations: isolate, square or split into cases,
  check every root.
- Exponential and logarithmic equations: same base, taking logs, combining logs.
- Every answer is substituted back as the last step; `mathlint solve` on the
  command line.

### v0.6 — Many unknowns

- Several equations, one per line; the unknowns are found automatically.
- Linear systems with a method switcher: substitution, elimination, Cramer's
  rule, Gaussian elimination, the inverse matrix.
- No solution and infinitely many solutions explained, with the general
  solution in terms of free variables.
- Nonlinear systems in two unknowns, solved by substitution and verified.
- "Solve for y": rearranging formulas with several letters.
- The checker learns systems: check your own working on a system, line by line.

### v0.7 — Calculator

Arithmetic with steps (order of operations, fractions, decimals and fractions,
percentages, powers and roots); expanding and factoring; simplifying rational,
radical, exponential, logarithmic and trigonometric expressions; a live answer
under the editor; an exact/decimal switch.

### v0.8 — Inequalities and graphs

Linear, quadratic, rational and absolute-value inequalities with sign charts and
interval answers on a number line; an interactive graph panel with solutions
marked; function analysis (domain, intercepts, zeros, asymptotes, extrema,
monotonicity, concavity).

### v0.9 — Calculus, complete

Limits with steps (substitution, factoring, conjugates, L'Hôpital, limits at
infinity); implicit and higher-order derivatives, tangent lines; partial
fractions and trigonometric substitution in full; area pictures; separable,
first-order linear and constant-coefficient second-order differential
equations; Taylor series.

### v0.10 — Premium, free

"Why?" on every step (the rule, a tiny example, the usual mistake); revealing one
step at a time and **trying the next step yourself**, checked by mathlint;
animated steps that highlight what changed; practice problems generated from the
one you solved; worked solutions for open-licensed textbooks such as OpenStax
(CC BY), in place of paywalled textbook solutions.

### v0.11 — App quality

Installable and offline (the engine is cached on the device), history and
favourites stored on the device, faster start-up with performance budgets,
screen-reader support for math, translated steps.

### v1.0 — App stores

Android and iOS apps built from the same web code (Capacitor), and a stable
Python package on PyPI.

### v1.x — Camera

Take or pick a photo and crop it; the math is recognised **on the device** and
lands in the editor, where you fix anything misread before solving. Printed math
first, handwriting after. Word problems, which need a language model, would only
ever be an opt-in extra.
