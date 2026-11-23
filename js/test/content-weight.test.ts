// The editing area and the source view pin their weight to a token so a host's
// body weight (500, 600) no longer becomes the content's, and strong/b (UA
// `bolder`) resolve from 400 to 700. The shell itself sets none, so the
// toolbar, menus and picker keep whatever the host gives them.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it } from "vitest";

import { declaredOn } from "./declared-on";

const STYLES = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../src/styles.css"),
  "utf8",
);
const USE = "var(--tiptap-content-weight, 400)";

afterEach(() => {
  document.head.innerHTML = "";
});

function rootDefault(name: string): string[] {
  const style = document.createElement("style");
  style.textContent = STYLES;
  document.head.appendChild(style);
  const sheet = style.sheet;
  if (!sheet) {
    throw new Error("styles.css did not parse");
  }
  return Array.from(sheet.cssRules)
    .filter((rule): rule is CSSStyleRule => rule instanceof CSSStyleRule)
    .filter((rule) => rule.selectorText === ":where(:root, :host)")
    .map((rule) => rule.style.getPropertyValue(name).trim())
    .filter((value) => value !== "");
}

describe("content weight token", () => {
  it("defaults to 400 on the root, beside the other tokens", () => {
    expect(rootDefault("--tiptap-content-weight")).toEqual(["400"]);
  });

  it("weights the editing area from the token", () => {
    expect(declaredOn(".django-tiptap .ProseMirror", "font-weight")).toEqual([USE]);
  });

  it("weights the source view from the same token", () => {
    expect(declaredOn(".django-tiptap__source", "font-weight")).toEqual([USE]);
  });

  it("leaves the shell's weight to the host, so the chrome keeps inheriting", () => {
    expect(declaredOn(".django-tiptap", "font-weight")).toEqual([]);
  });
});
