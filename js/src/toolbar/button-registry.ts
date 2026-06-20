// Toolbar button registry. Built-in buttons are pre-registered; consumers add
// their own via ui.registerButton(key, spec) and reference the key in
// config.toolbar. Unknown keys fail loudly at render time.
import type { Editor } from "../tiptap-runtime";

export interface ButtonSpec {
  icon: string;
  title: string;
  group?: string;
  isActive?: (editor: Editor) => boolean;
  isEnabled?: (editor: Editor) => boolean;
  onClick: (editor: Editor) => void;
}

const buttons = new Map<string, ButtonSpec>();

export function registerButton(key: string, spec: ButtonSpec): void {
  buttons.set(key, spec);
}

export function getButton(key: string): ButtonSpec | undefined {
  return buttons.get(key);
}
