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

## Data the recognizer learned from

The handwriting recognizer (since v0.12, `recognizer.bin`) was trained on
formulas generated in `training/`, drawn with symbols from these sources. None
of them is served with the app; the trained model is a Produced Work of the two
databases.

| Source | Used for | License |
| --- | --- | --- |
| [Detexify](https://detexify.kirelabs.org) training data by Daniel Kirsch | Handwritten math symbols, as strokes | [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/) |
| [HASYv2](https://doi.org/10.5281/zenodo.259444) by Martin Thoma | Handwritten symbols, digits and letters | [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/) |
| 29 handwriting fonts from [Google Fonts](https://github.com/google/fonts) (listed in `training/mathrec/fonts.py`) | Letters, digits and punctuation | SIL Open Font License 1.1 or Apache 2.0 |
| STIX Two Math, Noto Sans Math, Libertinus Math, Noto Serif, Noto Sans | Printed formulas | SIL Open Font License 1.1 |
| Latin Modern Math | Printed formulas | GUST Font License |

Contains information from the Detexify and HASYv2 databases, which are made
available under the Open Database License (ODbL).
