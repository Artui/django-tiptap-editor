// The editor's size and theme reach it through CSS custom properties, and each
// of the three routes in had a way to arrive and change nothing:
//
// - height / maxHeight from config are written onto the shell as
//   --tiptap-height / --tiptap-max-height. init() is public, so a value the
//   Python validator never saw ("auto", 500, "50%") was written as given and
//   sized the editor to its toolbar. The same truth table the Python suite runs
//   through validate_config (fixtures/css-lengths.json) runs here through init().
// - maxHeight did not exist: height is a minimum, so the editor grew with its
//   content forever.
// - ui.setTokens writes onto :root, while styles.css declared every default on
//   .django-tiptap itself. An element's own declaration beats an inherited one,
//   so a token set on :root (by setTokens or by plain CSS) never reached the
//   editor. jsdom neither inherits custom properties nor resolves var(), so a
//   computed-style assertion would read "" before and after the fix alike; the
//   check below is on the cascade's inputs instead: no rule declaring a
//   --tiptap-* default may match the shell or anything inside it.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import { toggleSourceView } from "../src/toolbar/source-view";
import lengths from "./fixtures/css-lengths.json";

// Joined from the module's path string: under jsdom the global URL is jsdom's,
// which fileURLToPath does not accept.
const STYLES = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../src/styles.css"),
  "utf8",
);

let mounted: string[] = [];
let errors: ReturnType<typeof vi.spyOn>;

function mount(config: Record<string, unknown>): HTMLElement {
  const id = `height-${mounted.length}`;
  const textarea = document.createElement("textarea");
  textarea.id = id;
  document.body.appendChild(textarea);
  DjangoTipTap.init(textarea, config);
  mounted.push(id);
  const shell = document.querySelector<HTMLElement>(`[data-tiptap-shell="${id}"]`);
  if (!shell) {
    throw new Error("no shell mounted");
  }
  return shell;
}

beforeEach(() => {
  errors = vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  for (const id of mounted) {
    DjangoTipTap.destroy(id);
  }
  mounted = [];
  vi.restoreAllMocks();
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  document.documentElement.removeAttribute("style");
});

const PROPERTIES = { height: "--tiptap-height", maxHeight: "--tiptap-max-height" } as const;

describe.each(Object.entries(PROPERTIES))("config.%s", (key, property) => {
  it.each(lengths.accepted)("writes the CSS length %j onto the shell", (value) => {
    const shell = mount({ [key]: value });
    expect(shell.style.getPropertyValue(property)).toBe(value);
    expect(errors).not.toHaveBeenCalled();
  });

  it.each(lengths.rejected)("refuses %j, leaving the default in place", (value) => {
    const shell = mount({ [key]: value });
    expect(shell.style.getPropertyValue(property)).toBe("");
    // "" is falsy, so it never reached the write; anything else is reported.
    if (value !== "") {
      expect(errors).toHaveBeenCalledWith(expect.stringContaining(`${key} must be a CSS length`));
    }
  });

  it("reads null as omitted, which is how a field drops a project-wide value", () => {
    // validate_config passes None through, and the widget writes it as null.
    const shell = mount({ [key]: null });
    expect(shell.style.getPropertyValue(property)).toBe("");
    expect(errors).not.toHaveBeenCalled();
  });

  it.each([500, true, ["500px"]])("refuses the non-string %j", (value) => {
    const shell = mount({ [key]: value });
    expect(shell.style.getPropertyValue(property)).toBe("");
    expect(errors).toHaveBeenCalledWith(expect.stringContaining(`${key} must be a CSS length`));
  });
});

function stylesheet(): CSSStyleRule[] {
  const style = document.createElement("style");
  style.textContent = STYLES;
  document.head.appendChild(style);
  return Array.from(style.sheet?.cssRules ?? []).filter(
    (rule): rule is CSSStyleRule => rule instanceof CSSStyleRule,
  );
}

function declared(rule: CSSStyleRule): string[] {
  return Array.from({ length: rule.style.length }, (_, i) => rule.style[i]);
}

describe("design tokens", () => {
  it("declares no --tiptap-* default on the shell or inside it", () => {
    const rules = stylesheet();
    const shell = mount({ height: "200px" });
    const inside = [shell, ...Array.from(shell.querySelectorAll("*"))];
    const shadowing = rules
      .filter((rule) => declared(rule).some((name) => name.startsWith("--tiptap-")))
      .filter((rule) => inside.some((el) => el.matches(rule.selectorText)))
      .map((rule) => rule.selectorText);
    expect(shadowing).toEqual([]);
  });

  it("declares the defaults where a token on :root overrides them", () => {
    // Zero specificity, so a project's :root, html or .django-tiptap rule wins
    // over the default whatever order the stylesheets load in.
    const defaults = stylesheet().filter((rule) =>
      declared(rule).some((name) => name.startsWith("--tiptap-")),
    );
    expect(defaults.map((rule) => rule.selectorText)).toEqual([":where(:root)"]);
    expect(document.documentElement.matches(":where(:root)")).toBe(true);
  });

  it("setTokens writes the token onto :root, under the per-instance config", () => {
    const shell = mount({ height: "200px" });
    DjangoTipTap.ui.setTokens({ border: "#ff0000", "--tiptap-height": "900px" });
    const root = document.documentElement.style;
    expect(root.getPropertyValue("--tiptap-border")).toBe("#ff0000");
    expect(root.getPropertyValue("--tiptap-height")).toBe("900px");
    // The shell's own (inline) value is what its contents inherit, so a field's
    // height still beats a page-wide token.
    expect(shell.style.getPropertyValue("--tiptap-height")).toBe("200px");
  });
});

describe("maxHeight caps the editing area", () => {
  it("is read by the scrolling content region, so the toolbar stays outside it", () => {
    const content = stylesheet().find((rule) => rule.selectorText === ".django-tiptap__content");
    expect(content?.style.getPropertyValue("max-height")).toBe("var(--tiptap-max-height)");
    expect(content?.style.getPropertyValue("overflow-y")).toBe("auto");
    const shell = mount({ maxHeight: "300px" });
    const toolbar = shell.querySelector(".django-tiptap__toolbar");
    expect(toolbar).not.toBeNull();
    expect(toolbar?.closest(".django-tiptap__content")).toBeNull();
  });

  it("caps source view too, which opens inside the same region", () => {
    mount({ maxHeight: "300px" });
    const editor = DjangoTipTap.get(mounted[0]);
    if (!editor) {
      throw new Error("no editor");
    }
    toggleSourceView(editor);
    const source = document.querySelector(".django-tiptap__source");
    expect(source?.parentElement?.classList.contains("django-tiptap__content")).toBe(true);
    toggleSourceView(editor);
  });
});
