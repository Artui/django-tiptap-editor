// DjangoTipTap.ui — the UI customization surface, in descending stability order:
//   tier 1  setTokens / registerButton   — stable, the default path
//   tier 2  setRenderer(region, fn)       — semi-stable (toolbar | statusbar)
//   tier 3  setShellRenderer(fn)          — advanced / experimental
import { setRenderer, setShellRenderer } from "./renderers";
import type {
  RegionContext,
  RegionRenderer,
  ShellContext,
  ShellRenderer,
} from "./renderers";
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
  setRenderer,
  setShellRenderer,
};

export type { ButtonSpec, RegionContext, RegionRenderer, ShellContext, ShellRenderer };
