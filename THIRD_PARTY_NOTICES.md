# Third-party content

`web/textbook-problems.json` contains adapted exercises from *College Algebra
with Corequisite Support 2e* by OpenStax. The textbook content is licensed under
the [Creative Commons Attribution 4.0 International
License](https://creativecommons.org/licenses/by/4.0/). The exercises were
transcribed into mathlint's plain-text notation; mathlint generates its own
worked solutions.

Access the original book free at
https://openstax.org/books/college-algebra-corequisite-support-2e/pages/1-introduction-to-prerequisites.

The OpenStax name and logos are not covered by the Creative Commons license.
The project's PolyForm license does not replace or restrict the CC BY 4.0
permissions that apply to this OpenStax material.

## Software served with the web app

Since v0.11 the web app serves these from its own site (`_site/vendor`, built by
`scripts/vendor.py`) instead of loading them from a CDN. Each keeps its own
license; the license files are copied next to the files where the package ships
one.

| Component | Version | License |
| --- | --- | --- |
| [Pyodide](https://pyodide.org) (with CPython's standard library) | 314.0.7 | MPL-2.0 (CPython: PSF License) |
| [SymPy](https://www.sympy.org) | as pinned by Pyodide's lock file | BSD-3-Clause |
| [mpmath](https://mpmath.org) | as pinned by Pyodide's lock file | BSD-3-Clause |
| [KaTeX](https://katex.org) and its fonts | 0.16.11 | MIT |
| [MathLive](https://cortexjs.io/mathlive/) and its fonts | 0.110.0 | MIT |
| [Figtree](https://github.com/erikdkennedy/figtree) (via Fontsource) | 5.3.0 | SIL Open Font License 1.1 |
| [Spline Sans Mono](https://github.com/SorkinType/SplineSansMono) (via Fontsource) | 5.3.0 | SIL Open Font License 1.1 |

The PolyForm Noncommercial license covers mathlint's own code only; it does not
replace or restrict the licenses above.
