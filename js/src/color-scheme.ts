// TIPTAP_COLOR_SCHEME reaches the page as data-tiptap-color-scheme on each
// textarea the widget renders. styles.css reads the scheme from <html> only
// (a rule on the shell would beat setTokens), so the glue copies it there once.
// A value already on <html> wins: the host's own template or toggle decides.
const SETTING_ATTR = "data-tiptap-color-scheme";
const THEME_ATTR = "data-tiptap-theme";
const SCHEMES = new Set(["light", "dark", "system"]);

export function applyColorScheme(element: HTMLElement): void {
  const scheme = element.getAttribute(SETTING_ATTR);
  const root = document.documentElement;
  if (scheme && SCHEMES.has(scheme) && !root.hasAttribute(THEME_ATTR)) {
    root.setAttribute(THEME_ATTR, scheme);
  }
}
