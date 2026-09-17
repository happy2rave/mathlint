export const EXAMPLES = [
  {
    name: "Derivative with a sign slip",
    text: `d/dx [x^2 sin x]
= 2x sin x + x^2 cos x
= x(2 sin x + x cos x)
= x(2 sin x - x cos x)`,
  },
  {
    name: "Integration by parts",
    text: `int x e^x dx
= x e^x - int e^x dx
= x e^x - e^x + C`,
  },
  {
    name: "Quadratic equation",
    text: `x^2 - 5x + 6 = 0
(x-2)(x-3) = 0
x = 2 or x = 3`,
  },
  {
    name: "Squaring invents a root",
    text: `sqrt(x) = x - 2
x = (x-2)^2
x = 1 or x = 4`,
  },
  {
    name: "Dividing loses a root",
    text: `x^2 = x
x = 1`,
  },
  {
    name: "Written in LaTeX",
    text: `\\frac{d}{dx} x^2 \\sin x
= 2x \\sin x + x^2 \\cos x
= x(2 \\sin x + x \\cos x)`,
  },
];
