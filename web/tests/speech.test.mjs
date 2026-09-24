import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { speak } from "../speech.js";

const dictionary = (lang) =>
  JSON.parse(readFileSync(new URL(`../locales/${lang}.json`, import.meta.url), "utf-8"));

function wordsFor(lang) {
  const english = dictionary("en");
  const words = lang === "en" ? english : dictionary(lang);
  return (key, args = {}) => {
    const template = words["speech." + key] ?? english["speech." + key];
    assert.ok(template !== undefined, `speech.${key} is missing`);
    return template.replace(/\{(\w+)\}/g, (_, name) => String(args[name]));
  };
}

const en = (latex) => speak(latex, wordsFor("en"));

test("numbers, letters and operators", () => {
  assert.equal(en("2 x + 3 = 7"), "2 x plus 3 equals 7");
  assert.equal(en(String.raw`a - b \cdot c`), "a minus b times c");
  assert.equal(en(String.raw`x \neq 1`), "x is not equal to 1");
  assert.equal(en(String.raw`x \leq 3`), "x is less than or equal to 3");
  assert.equal(en(String.raw`x \geq -2`), "x is greater than or equal to minus 2");
  assert.equal(en(String.raw`\approx 0.83`), "is approximately 0.83");
});

test("fractions, simple and nested", () => {
  assert.equal(en(String.raw`\frac{1}{2}`), "1 over 2");
  assert.equal(en(String.raw`\frac{x + 1}{x - 2}`), "the fraction x plus 1 over x minus 2, end of fraction");
});

test("powers, roots and subscripts", () => {
  assert.equal(en("x^{2}"), "x squared");
  assert.equal(en("x^3"), "x cubed");
  assert.equal(en("e^{x}"), "e to the power x");
  assert.equal(en("e^{2 x + 1}"), "e to the power 2 x plus 1, end of power");
  assert.equal(en(String.raw`\sqrt{x}`), "the square root of x");
  assert.equal(en(String.raw`\sqrt{x + 1}`), "the square root of x plus 1, end of root");
  assert.equal(en(String.raw`\sqrt[3]{8}`), "the root of index 3 of 8");
  assert.equal(en("x_{1}"), "x sub 1");
});

test("functions, brackets and absolute values", () => {
  assert.equal(en(String.raw`\sin{\left(x \right)}`), "sine of open bracket x close bracket");
  assert.equal(en(String.raw`\ln{\left(x \right)}`), "natural log of open bracket x close bracket");
  assert.equal(en(String.raw`\left|x - 1\right|`), "the absolute value of x minus 1, end of absolute value");
});

test("calculus", () => {
  assert.equal(en(String.raw`\int x\, dx`), "the integral of x d x");
  assert.equal(en(String.raw`\int\limits_{0}^{1} x^{2}\, dx`), "the integral from 0 to 1 of x squared d x");
  assert.equal(en(String.raw`\lim_{x \to 2} x^{2}`), "the limit as x tends to 2 of x squared");
  assert.equal(en(String.raw`\frac{d}{d x} x^{2}`), "the derivative with respect to x of x squared");
  assert.equal(en("f'(x)"), "f prime open bracket x close bracket");
  assert.equal(en(String.raw`\infty`), "infinity");
});

test("sets, words and matrices", () => {
  assert.equal(en(String.raw`x = 2 \quad\text{or}\quad x = 3`), "x equals 2, or, x equals 3");
  assert.equal(en(String.raw`x \in \mathbb{R}`), "x is in the real numbers");
  assert.equal(en(String.raw`\left\{2, 3\right\}`), "the set 2, 3");
  assert.equal(
    en(String.raw`\left[\begin{matrix}1 & 2\\3 & 4\end{matrix}\right]`),
    "a matrix with 2 rows and 2 columns: row 1: 1, 2; row 2: 3, 4"
  );
});

test("anything unknown is read out rather than dropped", () => {
  assert.equal(en(String.raw`\mysterious{x}`), "mysterious x");
});

test("the same math in Romanian, Russian and Spanish", () => {
  const latex = String.raw`\frac{1}{2} + x^{2} = \sqrt{y}`;
  assert.equal(speak(latex, wordsFor("ro")), "1 supra 2 plus x la pătrat egal cu radical din y");
  assert.equal(speak(latex, wordsFor("ru")), "1 делённое на 2 плюс x в квадрате равно квадратный корень из y");
  assert.equal(speak(latex, wordsFor("es")), "1 entre 2 más x al cuadrado es igual a la raíz cuadrada de y");
});
