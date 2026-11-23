// A portaled panel (no popover API) no longer inherits from the editor shell, so
// the shell's resolved theme is copied onto it inline at each open. A computed custom
// property already has var() substituted, so the private --_tiptap-* scheme
// values arrive resolved and need no copying of their own. The font is copied
// too: --tiptap-font defaults to inherit, which in a portal means <body>.
export const TOKEN_NAMES = [
  "--tiptap-height",
  "--tiptap-max-height",
  "--tiptap-font",
  "--tiptap-content-weight",
  "--tiptap-fg",
  "--tiptap-bg",
  "--tiptap-border",
  "--tiptap-radius",
  "--tiptap-toolbar-bg",
  "--tiptap-btn-fg",
  "--tiptap-btn-hover-bg",
  "--tiptap-btn-active-bg",
  "--tiptap-btn-active-fg",
  "--tiptap-accent",
  "--tiptap-content-bg",
  "--tiptap-content-fg",
  "--tiptap-content-border",
  "--tiptap-highlight-ink",
  "--tiptap-highlight-glyph-bg",
  "--tiptap-highlight-glyph-fg",
  "--tiptap-swatch-border",
  "--tiptap-swatch-border-hover",
  "--tiptap-shadow-color",
  "--tiptap-modal-shadow-color",
  "--tiptap-overlay-bg",
  "--tiptap-color-scheme",
] as const;

const INHERITED = ["font-family", "font-size", "line-height", "direction"] as const;

export function forwardTheme(from: Element, to: HTMLElement): void {
  const computed = getComputedStyle(from);
  for (const name of [...TOKEN_NAMES, ...INHERITED]) {
    const value = computed.getPropertyValue(name).trim();
    if (value) {
      to.style.setProperty(name, value);
    } else {
      to.style.removeProperty(name);
    }
  }
  const lang = from.closest<HTMLElement>("[lang]")?.lang;
  if (lang) {
    to.lang = lang;
  } else {
    to.removeAttribute("lang");
  }
}
