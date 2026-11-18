// What styles.css declares for a selector: jsdom cannot resolve var() or
// layout, so a use site is checked by reading the parsed rule.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const STYLES = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../src/styles.css"),
  "utf8",
);

export function declaredOn(selector: string, property: string): string[] {
  const style = document.createElement("style");
  style.textContent = STYLES;
  document.head.appendChild(style);
  const sheet = style.sheet;
  if (!sheet) {
    throw new Error("styles.css did not parse");
  }
  const values = Array.from(sheet.cssRules)
    .filter((rule): rule is CSSStyleRule => rule instanceof CSSStyleRule)
    .filter((rule) => rule.selectorText.split(",").some((part) => part.trim() === selector))
    .map((rule) => rule.style.getPropertyValue(property).trim())
    .filter((value) => value !== "");
  style.remove();
  return values;
}
