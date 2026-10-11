// The length rule for the height / maxHeight config keys. The Python side
// refuses anything else in validate_config, but init() is public and takes a
// config no validator saw, so the same rule runs here before a value becomes
// --tiptap-height / --tiptap-max-height. Both are held to one truth table,
// js/test/fixtures/css-lengths.json, whose unit list must equal
// constants.CSS_LENGTH_UNITS.
//
// A plain length is an unsigned number and a unit. A math function (calc / min
// / max / clamp) is checked lexically: every token is a number, a length, an
// arithmetic operator, a comma, whitespace, a parenthesis or one of those four
// functions; the parentheses balance and close at the very end; and at least
// one token is a length. That keeps out everything that is not arithmetic on
// lengths (var(), url(), percentages, quotes, ";", "!important"); whether the
// arithmetic is well formed is left to the browser. Percentages are refused on
// purpose: they resolve against a parent that rarely has a height, and then
// size the editor to nothing.

const VIEWPORT = ["", "s", "l", "d"].flatMap((size) =>
  ["vw", "vh", "vi", "vb", "vmin", "vmax"].map((axis) => `${size}${axis}`),
);

export const CSS_LENGTH_UNITS: ReadonlySet<string> = new Set([
  // absolute
  "px",
  "cm",
  "mm",
  "q",
  "in",
  "pt",
  "pc",
  // font-relative, and their root-relative forms
  "em",
  "rem",
  "ex",
  "rex",
  "ch",
  "rch",
  "cap",
  "rcap",
  "ic",
  "ric",
  "lh",
  "rlh",
  // viewport: default, small, large and dynamic
  ...VIEWPORT,
  // container query
  "cqw",
  "cqh",
  "cqi",
  "cqb",
  "cqmin",
  "cqmax",
]);

// Digits and whitespace are spelled out: JS's \s also matches a no-break space,
// which CSS does not treat as whitespace, and Python's \d matches any Unicode
// digit, so the two sides only agree on explicit ASCII classes. Units and
// function names are ASCII case-insensitive, as in CSS. Without the u flag, the
// i flag never folds a non-ASCII letter onto an ASCII one.
const NUMBER = String.raw`(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:e[-+]?[0-9]+)?`;
const PLAIN_LENGTH = new RegExp(String.raw`^${NUMBER}([a-z]+)$`, "i");
const MATH_START = /^(?:calc|min|max|clamp)\(/i;
// Sticky, so each match must start exactly where the previous one ended.
const MATH_TOKEN = new RegExp(
  String.raw`[ \t\n\r\f]+|(?:calc|min|max|clamp)?\(|\)|[-+*/,]|${NUMBER}([a-z]+)?`,
  "iy",
);

function isMathLength(value: string): boolean {
  let depth = 0;
  let hasLength = false;
  MATH_TOKEN.lastIndex = 0;
  while (MATH_TOKEN.lastIndex < value.length) {
    const token = MATH_TOKEN.exec(value);
    if (token === null) {
      return false;
    }
    if (token[0].endsWith("(")) {
      depth += 1;
    } else if (token[0] === ")") {
      depth -= 1;
      // The outer function closed before the end: "calc(1px) + 1px".
      if (depth === 0 && MATH_TOKEN.lastIndex < value.length) {
        return false;
      }
    } else if (token[1] !== undefined) {
      if (!CSS_LENGTH_UNITS.has(token[1].toLowerCase())) {
        return false;
      }
      hasLength = true;
    }
  }
  return depth === 0 && hasLength;
}

export function isCssLength(value: unknown): value is string {
  if (typeof value !== "string") {
    return false;
  }
  // JS's $ does not match before a trailing newline (no m flag), unlike
  // Python's, which is why the Python side uses fullmatch.
  const plain = PLAIN_LENGTH.exec(value);
  if (plain !== null) {
    return CSS_LENGTH_UNITS.has(plain[1].toLowerCase());
  }
  return MATH_START.test(value) && isMathLength(value);
}
