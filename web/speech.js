// Math read aloud: the LaTeX mathlint writes, turned into words.
//
//   speak(String.raw`\frac{1}{2} + x^{2}`, words)  ->  "1 over 2 plus x squared"
//
// `words(key, args)` supplies the language (the "speech.*" entries of the
// dictionaries), so a screen reader says the math in the reader's language:
// TalkBack, VoiceOver and NVDA read these words the same way, where MathML
// support differs from one to the next.
//
// It reads the LaTeX that SymPy and mathlint's editor produce: fractions,
// powers, roots, functions, brackets, absolute values, sets, matrices,
// integrals, limits, derivatives and a few words in \text{}. Anything it does
// not know is read out by name rather than dropped.

const RELATIONS = {
  "=": "equals",
  "<": "less",
  ">": "greater",
  "\\le": "lessEqual",
  "\\leq": "lessEqual",
  "\\leqslant": "lessEqual",
  "\\ge": "greaterEqual",
  "\\geq": "greaterEqual",
  "\\geqslant": "greaterEqual",
  "\\ne": "notEqual",
  "\\neq": "notEqual",
  "\\approx": "approx",
  "\\in": "in",
  "\\Rightarrow": "implies",
  "\\implies": "implies",
  "\\sim": "rowEquivalent",
};

const SYMBOLS = {
  "+": "plus",
  "-": "minus",
  "\\cdot": "times",
  "\\times": "times",
  "\\div": "dividedBy",
  "\\pm": "plusMinus",
  "\\mp": "minusPlus",
  "\\infty": "infinity",
  "\\cup": "union",
  "\\cap": "intersection",
  "\\emptyset": "emptySet",
  "\\varnothing": "emptySet",
  "\\dots": "dots",
  "\\ldots": "dots",
  "\\cdots": "dots",
  "\\to": "tendsTo",
  "!": "factorial",
  "'": "prime",
};

const GREEK = new Set([
  "pi", "theta", "alpha", "beta", "gamma", "delta", "lambda", "mu", "phi", "varphi", "omega", "sigma",
]);

const FUNCTIONS = {
  sin: "sin", cos: "cos", tan: "tan", cot: "cot", sec: "sec", csc: "csc",
  ln: "ln", log: "log", exp: "exp",
  asin: "asin", acos: "acos", atan: "atan", arcsin: "asin", arccos: "acos", arctan: "atan",
  sinh: "sinh", cosh: "cosh", tanh: "tanh",
};

// \, \; \quad and friends: space, or a pause in speech
const QUIET = new Set(["\\,", "\\;", "\\!", "\\ ", "\\:", "\\displaystyle", "\\limits", "\\left.", "\\right.", "\\big", "\\Big"]);
const PAUSE = new Set(["\\quad", "\\qquad"]);

export function speak(latex, words) {
  const reader = new Reader(tokenize(String(latex)), words);
  const spoken = reader.sequence(() => false);
  return tidy(spoken);
}

function tidy(text) {
  return text
    .replace(/\s+/g, " ")
    .replace(/ ([,;:])/g, "$1")
    .replace(/([,;:])(?:[,;:] ?)+/g, "$1 ")
    .replace(/^[,;: ]+|[,;: ]+$/g, "")
    .trim();
}

function tokenize(latex) {
  const tokens = [];
  let index = 0;
  while (index < latex.length) {
    const char = latex[index];
    if (char === "\\") {
      const command = latex.slice(index).match(/^\\([A-Za-z]+|.)/);
      let name = "\\" + command[1];
      index += command[0].length;
      // \left( and \right| are one token with their bracket
      if (name === "\\left" || name === "\\right") {
        const bracket = latex.slice(index).match(/^\s*(\\\{|\\\}|\\\||\\langle|\\rangle|.)/);
        name += bracket[1];
        index += bracket[0].length;
      }
      tokens.push(name);
    } else if (/\s/.test(char)) {
      index += 1;
    } else if (/[0-9.]/.test(char)) {
      const number = latex.slice(index).match(/^[0-9]*\.?[0-9]+|^[0-9]+/);
      tokens.push(number ? number[0] : char);
      index += number ? number[0].length : 1;
    } else {
      tokens.push(char);
      index += 1;
    }
  }
  return tokens;
}

class Reader {
  constructor(tokens, words) {
    this.tokens = tokens;
    this.at = 0;
    this.words = words;
  }

  peek() {
    return this.tokens[this.at];
  }

  next() {
    return this.tokens[this.at++];
  }

  w(key, args) {
    return this.words(key, args);
  }

  // Everything up to (not including) the token that `stop` accepts.
  sequence(stop) {
    const parts = [];
    while (this.at < this.tokens.length && !stop(this.peek())) {
      const part = this.item(stop);
      if (part) parts.push(part);
    }
    return parts.join(" ");
  }

  // A braced group, or a single atom when there are no braces.
  argument() {
    if (this.peek() === "{") {
      this.next();
      const inside = this.sequence((token) => token === "}");
      this.next();
      return inside;
    }
    return this.item(() => false);
  }

  rawArgument() {
    // the tokens of a braced group, to look at before speaking them
    if (this.peek() !== "{") return [this.next()];
    const start = ++this.at;
    let depth = 1;
    while (this.at < this.tokens.length && depth) {
      const token = this.next();
      if (token === "{") depth += 1;
      if (token === "}") depth -= 1;
    }
    return this.tokens.slice(start, this.at - 1);
  }

  speakTokens(tokens) {
    return new Reader(tokens, this.words).sequence(() => false);
  }

  item(stop) {
    const token = this.peek();
    if (token in RELATIONS) {
      this.next();
      return this.w(RELATIONS[token]);
    }
    if (token === "}" || token === "&" || token === "\\\\") {
      this.next();
      return "";
    }
    return this.postfix(this.atom(stop));
  }

  // x^2, x_1 and f' after an atom
  postfix(base) {
    let spoken = base;
    for (;;) {
      const token = this.peek();
      if (token === "^") {
        this.next();
        spoken = this.power(spoken, this.rawArgument());
      } else if (token === "_") {
        this.next();
        spoken = this.w("sub", { base: spoken, index: this.speakTokens(this.rawArgument()) });
      } else if (token === "'") {
        this.next();
        spoken = `${spoken} ${this.w("prime")}`;
      } else {
        return spoken;
      }
    }
  }

  power(base, exponent) {
    const text = exponent.join("");
    if (text === "2") return this.w("squared", { base });
    if (text === "3") return this.w("cubed", { base });
    if (text === "+") return `${base} ${this.w("fromRight")}`;
    if (text === "-") return `${base} ${this.w("fromLeft")}`;
    const spoken = this.speakTokens(exponent);
    return this.w(exponent.length === 1 ? "power" : "powerLong", { base, exponent: spoken });
  }

  // What follows an integral, a limit or d/dx: up to the next relation.
  body(stop) {
    return this.sequence((token) => stop(token) || token in RELATIONS || PAUSE.has(token));
  }

  atom(stop) {
    const token = this.next();
    if (token === "{") {
      const inside = this.sequence((next) => next === "}");
      this.next();
      return inside;
    }
    if (/^[0-9.]+$/.test(token) || /^[A-Za-z]$/.test(token)) return token;
    if (token in SYMBOLS) return this.w(SYMBOLS[token]);
    if (token === "(") return this.w("openBracket");
    if (token === ")") return this.w("closeBracket");
    if (token === "[") return this.w("openSquare");
    if (token === "]") return this.w("closeSquare");
    if (token === "," || token === ";" || token === ":") return token;
    if (QUIET.has(token)) return "";
    if (PAUSE.has(token)) return ",";
    if (token.startsWith("\\left")) return this.bracketed(token.slice(5));
    if (token.startsWith("\\right")) return "";

    const name = token.slice(1);
    if (GREEK.has(name)) return this.w("greek." + (name === "varphi" ? "phi" : name));
    if (name in FUNCTIONS) return this.func(this.w("fn." + FUNCTIONS[name]));
    switch (token) {
      case "\\operatorname": {
        const inner = this.rawArgument().join("");
        const key = FUNCTIONS[inner];
        return this.func(key ? this.w("fn." + key) : inner);
      }
      case "\\frac":
      case "\\dfrac":
      case "\\tfrac":
        return this.fraction(stop);
      case "\\sqrt":
        return this.root();
      case "\\text":
      case "\\textrm":
      case "\\mathrm":
      case "\\mathit":
      case "\\operatorname*":
        return this.rawArgument().join("");
      case "\\mathbb": {
        const set = this.rawArgument().join("");
        return set === "R" ? this.w("realNumbers") : set;
      }
      case "\\int":
        return this.integral(stop);
      case "\\lim":
        return this.limit(stop);
      case "\\begin":
        return this.matrix();
      case "\\end":
        this.rawArgument();
        return "";
      default:
        return name;
    }
  }

  func(name) {
    let spoken = name;
    if (this.peek() === "^") {
      this.next();
      const exponent = this.rawArgument();
      spoken = exponent.join("") === "-1" ? this.w("inverse", { f: name }) : this.power(name, exponent);
    }
    return this.w("of", { f: spoken, x: this.argument() });
  }

  fraction(stop) {
    const top = this.rawArgument();
    const bottom = this.rawArgument();
    // d/dx and d^2/dx^2 act on what follows
    if (top[0] === "d" && bottom[0] === "d" && (top.length === 1 || top[1] === "^")) {
      const variable = bottom[1];
      const body = this.body(stop);
      if (top.length === 1) return this.w("derivative", { x: variable, body });
      const order = top[2] === "{" ? top[3] : top[2];
      return this.w("derivativeN", { n: order, x: variable, body });
    }
    const a = this.speakTokens(top);
    const b = this.speakTokens(bottom);
    const simple = top.length === 1 && bottom.length === 1;
    return this.w(simple ? "over" : "fraction", { a, b });
  }

  root() {
    let index = null;
    if (this.peek() === "[") {
      this.next();
      const start = this.at;
      while (this.at < this.tokens.length && this.peek() !== "]") this.next();
      index = this.speakTokens(this.tokens.slice(start, this.at));
      this.next();
    }
    const inside = this.rawArgument();
    const x = this.speakTokens(inside);
    if (index) return this.w("root", { n: index, x });
    return this.w(inside.length === 1 ? "sqrt" : "sqrtLong", { x });
  }

  bracketed(opening) {
    // a matrix brings its own brackets: say only the matrix
    if (this.peek() === "\\begin") {
      this.next();
      const matrix = this.matrix();
      if (this.peek()?.startsWith("\\right")) this.next();
      return matrix;
    }
    const inside = this.sequence((token) => token.startsWith("\\right"));
    const closing = this.next() || "";
    if (opening === "|") return this.w("abs", { x: inside });
    if (opening === "\\{") return this.w("setOf", { items: inside });
    const open = { "(": "openBracket", "[": "openSquare" }[opening];
    const close = { "\\right)": "closeBracket", "\\right]": "closeSquare" }[closing];
    return [open && this.w(open), inside, close && this.w(close)].filter(Boolean).join(" ");
  }

  integral(stop) {
    let lower = null;
    let upper = null;
    while (this.peek() === "_" || this.peek() === "^" || this.peek() === "\\limits") {
      const token = this.next();
      if (token === "_") lower = this.speakTokens(this.rawArgument());
      if (token === "^") upper = this.speakTokens(this.rawArgument());
    }
    const body = this.body(stop);
    if (lower !== null && upper !== null) return this.w("integralFrom", { a: lower, b: upper, body });
    return this.w("integral", { body });
  }

  limit(stop) {
    let approach = "";
    if (this.peek() === "_") {
      this.next();
      approach = this.speakTokens(this.rawArgument());
    }
    return this.w("limit", { approach, body: this.body(stop) });
  }

  matrix() {
    this.rawArgument(); // matrix, pmatrix, bmatrix...
    const rows = [[]];
    let cell = [];
    while (this.at < this.tokens.length && this.peek() !== "\\end") {
      const token = this.next();
      if (token === "&") {
        rows.at(-1).push(cell);
        cell = [];
      } else if (token === "\\\\") {
        rows.at(-1).push(cell);
        cell = [];
        rows.push([]);
      } else {
        cell.push(token);
      }
    }
    rows.at(-1).push(cell);
    this.next();
    this.rawArgument();
    const filled = rows.filter((row) => row.some((entry) => entry.length));
    const spokenRows = filled.map((row, index) =>
      this.w("row", { n: index + 1, cells: row.map((entry) => this.speakTokens(entry)).join(", ") })
    );
    return this.w("matrix", {
      rows: filled.length,
      cols: Math.max(...filled.map((row) => row.length)),
      content: spokenRows.join("; "),
    });
  }
}
