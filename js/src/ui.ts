// DjangoTipTap.ui — the UI customization surface. Tier 1 (design tokens) and the
// toolbar button registry are here; region / shell renderers layer on later.
import { registerButton } from "./toolbar/button-registry";
import type { ButtonSpec } from "./toolbar/button-registry";

// Design-token theming (the stable, default customization path). Sets
// `--tiptap-*` custom properties on the document root; bare keys are prefixed.
export function setTokens(tokens: Record<string, string>): void {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(tokens)) {
    root.style.setProperty(key.startsWith("--") ? key : `--tiptap-${key}`, value);
  }
}

export const ui = {
  registerButton,
  setTokens,
};

export type { ButtonSpec };
