import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it } from "vitest";

import { forwardTheme, TOKEN_NAMES } from "../src/toolbar/forward-theme";

const STYLES = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../src/styles.css"),
  "utf8",
);

afterEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
});

describe("forwardTheme", () => {
  it("names every token the stylesheet declares a default for, in order", () => {
    const block = /:where\(:root, :host\)\s*\{([^}]*)\}/.exec(STYLES)?.[1] ?? "";
    const declared = Array.from(block.matchAll(/^\s*(--tiptap-[\w-]+)\s*:/gm), (m) => m[1]);
    expect(declared.length).toBeGreaterThan(0);
    expect([...TOKEN_NAMES]).toEqual(declared);
  });

  it("copies the source's tokens and lang, and clears what the source no longer sets", () => {
    const style = document.createElement("style");
    style.textContent = ".source { --tiptap-fg: rgb(4, 5, 6); font-family: Georgia; }";
    document.head.appendChild(style);
    const wrapper = document.createElement("div");
    wrapper.lang = "de";
    const source = document.createElement("div");
    source.className = "source";
    wrapper.appendChild(source);
    document.body.appendChild(wrapper);
    const panel = document.createElement("div");
    panel.style.setProperty("--tiptap-bg", "red");

    forwardTheme(source, panel);

    expect(panel.style.getPropertyValue("--tiptap-fg")).toBe("rgb(4, 5, 6)");
    expect(panel.style.fontFamily).toBe("Georgia");
    expect(panel.style.getPropertyValue("--tiptap-bg")).toBe("");
    expect(panel.lang).toBe("de");
    wrapper.removeAttribute("lang");
    forwardTheme(source, panel);
    expect(panel.hasAttribute("lang")).toBe(false);
  });
});
