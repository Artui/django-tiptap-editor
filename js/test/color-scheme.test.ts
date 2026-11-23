// The dark scheme is a set of private --_tiptap-* values on <html>, picked by
// data-tiptap-theme. jsdom has no matchMedia and resolves no var(), so these
// checks read the stylesheet's rules: what each scheme declares, where, in
// which order, and the contrast of the pairs the stylesheet puts together.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it } from "vitest";

import { applyColorScheme } from "../src/color-scheme";
import DjangoTipTap from "../src/index";
import { declaredOn } from "./declared-on";

const HERE = dirname(fileURLToPath(import.meta.url));
const STYLES = readFileSync(join(HERE, "../src/styles.css"), "utf8");
const BUTTONS = readFileSync(join(HERE, "../src/toolbar/built-in-buttons.ts"), "utf8");
const HIGHLIGHTS = JSON.parse(
  (/const HIGHLIGHTS = (\[[^\]]*\]);/.exec(BUTTONS)?.[1] ?? "[]").replace(/'/g, '"'),
) as string[];

const NOT_COLOURS = new Set(["height", "max-height", "font", "content-weight", "radius", "modal-z"]);
const DARK = ':where(html[data-tiptap-theme="dark"])';
const SYSTEM = ':where(html[data-tiptap-theme="system"])';
const LIGHT = ':where(html[data-tiptap-theme="light"])';

let mounted: string[] = [];

afterEach(() => {
  for (const id of mounted) {
    DjangoTipTap.destroy(id);
  }
  mounted = [];
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  document.documentElement.removeAttribute("data-tiptap-theme");
});

interface Located {
  rule: CSSStyleRule;
  media: string | null;
  index: number;
}

function rules(): Located[] {
  const style = document.createElement("style");
  style.textContent = STYLES;
  document.head.appendChild(style);
  const sheet = style.sheet;
  if (!sheet) {
    throw new Error("styles.css did not parse");
  }
  return Array.from(sheet.cssRules).flatMap((rule, index): Located[] => {
    if (rule instanceof CSSStyleRule) {
      return [{ rule, media: null, index }];
    }
    if (rule instanceof CSSMediaRule) {
      return Array.from(rule.cssRules)
        .filter((inner): inner is CSSStyleRule => inner instanceof CSSStyleRule)
        .map((inner) => ({ rule: inner, media: rule.conditionText, index }));
    }
    return [];
  });
}

function declarations(rule: CSSStyleRule): Map<string, string> {
  const names = Array.from({ length: rule.style.length }, (_, i) => rule.style[i]);
  return new Map(names.map((name) => [name, rule.style.getPropertyValue(name).trim()]));
}

function schemeRule(selector: string, media: string | null = null): Located {
  const found = rules().filter(
    (entry) => entry.rule.selectorText === selector && entry.media === media,
  );
  expect(found).toHaveLength(1);
  return found[0];
}

function colourTokens(): string[] {
  const root = schemeRule(":where(:root, :host)");
  return Array.from(declarations(root.rule).keys())
    .filter((name) => name.startsWith("--tiptap-"))
    .map((name) => name.slice("--tiptap-".length))
    .filter((name) => !NOT_COLOURS.has(name));
}

function mount(html = "<p>x</p>"): HTMLElement {
  const id = `scheme-${mounted.length}`;
  const textarea = document.createElement("textarea");
  textarea.id = id;
  textarea.value = html;
  document.body.appendChild(textarea);
  DjangoTipTap.init(textarea, {});
  mounted.push(id);
  const shell = document.querySelector<HTMLElement>(`[data-tiptap-shell="${id}"]`);
  if (!shell) {
    throw new Error("no shell mounted");
  }
  return shell;
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((at) => parseInt(hex.slice(at, at + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// The colours each scheme paints with. Light: the root fallbacks, and the
// content tokens' use-site fallbacks (content-bg falls back to bg, and so on).
function palette(scheme: "light" | "dark"): Record<string, string> {
  if (scheme === "dark") {
    const dark = declarations(schemeRule(DARK).rule);
    return Object.fromEntries(colourTokens().map((name) => [name, dark.get(`--_tiptap-${name}`) ?? ""]));
  }
  const root = declarations(schemeRule(":where(:root, :host)").rule);
  const light: Record<string, string> = {};
  for (const name of colourTokens()) {
    light[name] = /,\s*(#[0-9a-f]{6})\)$/i.exec(root.get(`--tiptap-${name}`) ?? "")?.[1] ?? "";
  }
  light["content-bg"] = light.bg;
  light["content-fg"] = light.fg;
  light["highlight-glyph-fg"] = light["btn-fg"];
  return light;
}

describe("the dark set", () => {
  it("gives every light colour token a dark value, in both dark rules", () => {
    const tokens = colourTokens();
    expect(tokens.length).toBeGreaterThan(9);
    const dark = declarations(schemeRule(DARK).rule);
    const system = declarations(schemeRule(SYSTEM, "(prefers-color-scheme: dark)").rule);
    for (const name of tokens) {
      expect(dark.get(`--_tiptap-${name}`), name).toBeTruthy();
    }
    expect(Object.fromEntries(system)).toEqual(Object.fromEntries(dark));
  });

  it("reads each colour token through its private value", () => {
    const root = declarations(schemeRule(":where(:root, :host)").rule);
    for (const name of colourTokens()) {
      expect(root.get(`--tiptap-${name}`), name).toMatch(
        new RegExp(`^var\\(--_tiptap-${name}(,|\\)$)`),
      );
    }
  });

  it("declares no length, radius, font or z-index", () => {
    const declared = Array.from(declarations(schemeRule(DARK).rule).keys());
    expect(declared.every((name) => name.startsWith("--_tiptap-"))).toBe(true);
    const names = declared.map((name) => name.slice("--_tiptap-".length));
    expect(names.filter((name) => NOT_COLOURS.has(name))).toEqual([]);
    expect(names.sort()).toEqual(colourTokens().sort());
  });

  it("is reset by forced light, which follows both dark rules in source order", () => {
    const light = schemeRule(LIGHT);
    const darkNames = Array.from(declarations(schemeRule(DARK).rule).keys()).sort();
    const lightDecls = declarations(light.rule);
    expect(Array.from(lightDecls.keys()).sort()).toEqual(darkNames);
    expect(new Set(lightDecls.values())).toEqual(new Set(["initial"]));
    expect(light.index).toBeGreaterThan(schemeRule(DARK).index);
    expect(light.index).toBeGreaterThan(
      schemeRule(SYSTEM, "(prefers-color-scheme: dark)").index,
    );
  });
});

describe("scheme rules", () => {
  it("are zero-specificity, at root, and match nothing in the editor", () => {
    const scheme = rules().filter(({ rule }) =>
      Array.from(declarations(rule).keys()).some((name) => /^--_?tiptap-/.test(name)),
    );
    expect(scheme.map(({ rule }) => rule.selectorText).sort()).toEqual(
      [":where(:root, :host)", DARK, LIGHT, SYSTEM].sort(),
    );
    const shell = mount();
    const inside = [shell, ...Array.from(shell.querySelectorAll("*"))];
    for (const theme of ["dark", "system", "light"]) {
      document.documentElement.setAttribute("data-tiptap-theme", theme);
      for (const { rule } of scheme) {
        expect(rule.selectorText).toMatch(/^:where\(.*\)$/s);
        const selector = rule.selectorText.replace(/\s*,\s*:host(?=\s*\))/, "");
        expect(inside.some((el) => el.matches(selector)), rule.selectorText).toBe(false);
      }
    }
    expect(document.documentElement.matches(DARK)).toBe(false);
    document.documentElement.setAttribute("data-tiptap-theme", "dark");
    expect(document.documentElement.matches(DARK)).toBe(true);
  });

  it("set color-scheme on the shell and the modal, never on the root", () => {
    const all = rules();
    const bySelector = (selector: string) =>
      all.find(({ rule }) => rule.selectorText === selector)?.rule.style.getPropertyValue(
        "color-scheme",
      );
    expect(bySelector(".django-tiptap")).toBe("var(--tiptap-color-scheme)");
    expect(bySelector(".django-tiptap__modal")).toContain("var(--tiptap-color-scheme");
    const rooted = all.filter(
      ({ rule }) => /:root|html/.test(rule.selectorText) && rule.style.getPropertyValue("color-scheme"),
    );
    expect(rooted).toEqual([]);
  });
});

describe("contrast", () => {
  const TEXT: [string, string][] = [
    ["fg", "bg"],
    ["fg", "btn-hover-bg"],
    ["btn-fg", "toolbar-bg"],
    ["btn-fg", "btn-hover-bg"],
    ["btn-active-fg", "btn-active-bg"],
    ["content-fg", "content-bg"],
    ["accent", "content-bg"],
    ["highlight-glyph-fg", "highlight-glyph-bg"],
  ];
  const NON_TEXT: [string, string][] = [
    ["btn-active-fg", "btn-active-bg"],
    ["accent", "bg"],
    ["accent", "toolbar-bg"],
    ["accent", "content-bg"],
    ["border", "bg"],
    ["border", "toolbar-bg"],
    ["border", "content-bg"],
  ];

  it.each(["light", "dark"] as const)("meets 4.5:1 for text and 3:1 for the rest (%s)", (scheme) => {
    const colours = palette(scheme);
    for (const [fg, bg] of TEXT) {
      expect(contrast(colours[fg], colours[bg]), `${fg} on ${bg}`).toBeGreaterThanOrEqual(4.5);
    }
    for (const [fg, bg] of NON_TEXT) {
      expect(contrast(colours[fg], colours[bg]), `${fg} on ${bg}`).toBeGreaterThanOrEqual(3);
    }
  });

  it("gives the dark paper a table border at 3:1 and a dark ink on every highlight", () => {
    const dark = palette("dark");
    expect(contrast(dark["content-border"], dark["content-bg"])).toBeGreaterThanOrEqual(3);
    const ink = declarations(schemeRule(DARK).rule).get("--_tiptap-highlight-ink") ?? "";
    expect(HIGHLIGHTS).toHaveLength(5);
    for (const highlight of HIGHLIGHTS) {
      expect(contrast(ink, highlight), highlight).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("makes the dark paper lighter than the chrome, and still dark", () => {
    const dark = palette("dark");
    expect(luminance(dark["content-bg"])).toBeGreaterThan(luminance(dark["toolbar-bg"]));
    expect(luminance(dark["content-bg"])).toBeGreaterThan(luminance(dark.bg));
    expect(luminance(dark["content-bg"])).toBeLessThan(0.1);
  });

  it("repeats the light border at the modal header's and picker item's fallbacks", () => {
    const border = palette("light").border;
    const sites = [
      ...declaredOn(".django-tiptap__modal-header", "border-bottom"),
      ...declaredOn(".django-tiptap__picker-item", "border"),
    ];
    expect(sites).toHaveLength(2);
    for (const site of sites) {
      expect(/(#[0-9a-f]{6})\)\)$/i.exec(site)?.[1], site).toBe(border);
    }
  });

  it("keeps light table cells at #d0d5dd and leaves both borders to a host's override", () => {
    expect(palette("light")["content-border"]).toBe("#d0d5dd");
    const root = declarations(schemeRule(":where(:root, :host)").rule);
    expect(root.get("--tiptap-content-border")).not.toContain("--tiptap-border");
    const declaring = rules().filter(({ rule }) =>
      ["--tiptap-border", "--tiptap-content-border"].some((name) => rule.style.getPropertyValue(name)),
    );
    expect(declaring.map(({ rule }) => rule.selectorText)).toEqual([":where(:root, :host)"]);
  });
});

describe("the highlight ink rule", () => {
  function inkSelector(): string {
    const found = rules().filter(
      ({ rule }) => rule.style.getPropertyValue("color") === "var(--tiptap-highlight-ink, currentColor)",
    );
    expect(found).toHaveLength(1);
    expect(found[0].rule.selectorText).toMatch(/^:where\(.*\)$/s);
    // jsdom's engine misreads a :not() chain inside :where(); matching the
    // inside alone gives the same answer.
    return found[0].rule.selectorText.replace(/^:where\((.*)\)$/s, "$1");
  }

  it("inks a highlight with no colour, and leaves an inline colour alone", () => {
    const shell = mount(
      '<p><span style="background-color: #fff3a3">plain</span> ' +
        '<span style="color: #e03e2d; background-color: #bfe3ff">red</span></p>',
    );
    const spans = Array.from(shell.querySelectorAll<HTMLElement>(".ProseMirror span"));
    const byText = (text: string) => spans.find((span) => span.textContent === text);
    const selector = inkSelector();
    expect(byText("plain")?.matches(selector)).toBe(true);
    expect(byText("red")?.matches(selector)).toBe(false);
  });

  it("leaves a run with a font-family or a font-size alone, however it sets colours", () => {
    const shell = mount(
      '<p><span style="font-family: Georgia; color: rgb(224, 62, 45); background-color: rgb(255, 243, 163)">family</span> ' +
        '<span style="font-size: 20px">size</span></p>',
    );
    const spans = Array.from(shell.querySelectorAll<HTMLElement>(".ProseMirror span"));
    const byText = (text: string) => spans.find((span) => span.textContent === text);
    const selector = inkSelector();
    expect(byText("family")).toBeDefined();
    expect(byText("family")?.matches(selector)).toBe(false);
    expect(byText("size")).toBeDefined();
    expect(byText("size")?.matches(selector)).toBe(false);
  });

  it("never changes the HTML the field posts", () => {
    const html =
      '<p><span style="color: #1f2329">dark</span> <span style="background-color: #fff3a3">hl</span> ' +
      '<span style="color: #e03e2d; background-color: #bfe3ff">both</span></p>';
    mount(html);
    const editor = DjangoTipTap.get(mounted[0]);
    const light = editor?.getHTML();
    document.documentElement.setAttribute("data-tiptap-theme", "dark");
    expect(editor?.getHTML()).toBe(light);
    expect(light).toContain("background-color: rgb(255, 243, 163)");
  });
});

describe("applyColorScheme", () => {
  function textarea(scheme?: string): HTMLTextAreaElement {
    const element = document.createElement("textarea");
    if (scheme !== undefined) {
      element.setAttribute("data-tiptap-color-scheme", scheme);
    }
    return element;
  }

  it.each(["light", "dark", "system"])("copies %s to <html>", (scheme) => {
    applyColorScheme(textarea(scheme));
    expect(document.documentElement.getAttribute("data-tiptap-theme")).toBe(scheme);
  });

  it("writes nothing when the setting is unset or unknown", () => {
    applyColorScheme(textarea());
    applyColorScheme(textarea("page"));
    expect(document.documentElement.hasAttribute("data-tiptap-theme")).toBe(false);
  });

  it("leaves a value the host set alone", () => {
    document.documentElement.setAttribute("data-tiptap-theme", "light");
    applyColorScheme(textarea("dark"));
    expect(document.documentElement.getAttribute("data-tiptap-theme")).toBe("light");
  });

  it("runs on mount", () => {
    const element = textarea("system");
    element.id = "scheme-mount";
    document.body.appendChild(element);
    DjangoTipTap.init(element, {});
    mounted.push(element.id);
    expect(document.documentElement.getAttribute("data-tiptap-theme")).toBe("system");
  });
});

describe("use sites jsdom cannot resolve through var()", () => {
  it("paints the editing area with the content tokens", () => {
    expect(declaredOn(".django-tiptap .ProseMirror", "color")).toEqual([
      "var(--tiptap-content-fg, currentColor)",
    ]);
    expect(declaredOn(".django-tiptap .ProseMirror", "background")).toEqual([
      "var(--tiptap-content-bg, transparent)",
    ]);
  });

  it("borders table cells with the content border, which has a default in every scheme", () => {
    for (const cell of [".django-tiptap .ProseMirror th", ".django-tiptap .ProseMirror td"]) {
      expect(declaredOn(cell, "border")).toEqual([
        "1px solid var(--tiptap-content-border, var(--tiptap-border))",
      ]);
    }
  });
});
