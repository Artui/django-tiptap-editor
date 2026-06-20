// Toolbar control registry. Built-in controls are pre-registered; consumers add
// their own via ui.registerButton(key, spec) and reference the key in
// config.toolbar. Unknown keys fail loudly at render time.
//
// A control is either a plain command button (icon + onClick) or a custom
// control that renders its own DOM (e.g. a dropdown) via `render`.
import type { Editor } from "../tiptap-runtime";

export interface RenderedControl {
  el: HTMLElement;
  refresh?: () => void;
}

export interface ButtonSpec {
  title: string;
  group?: string;
  // Command-button form:
  icon?: string;
  isActive?: (editor: Editor) => boolean;
  isEnabled?: (editor: Editor) => boolean;
  onClick?: (editor: Editor) => void;
  // Custom-control form (takes precedence): owns its rendering + refresh.
  render?: (editor: Editor) => RenderedControl;
}

const buttons = new Map<string, ButtonSpec>();

export function registerButton(key: string, spec: ButtonSpec): void {
  buttons.set(key, spec);
}

export function getButton(key: string): ButtonSpec | undefined {
  return buttons.get(key);
}
