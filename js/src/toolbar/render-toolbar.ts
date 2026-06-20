// Builds the toolbar DOM for an editor and returns a refresh() that syncs every
// button's active / enabled state. Buttons preserve the editor selection on
// click (mousedown preventDefault) so commands apply to the current range.
import type { TipTapConfig } from "../default-config";
import { DEFAULT_TOOLBAR } from "../default-config";
import type { Editor } from "../tiptap-runtime";
import { getButton } from "./button-registry";
import type { ButtonSpec } from "./button-registry";

export interface RenderedToolbar {
  el: HTMLElement;
  refresh: () => void;
}

export function renderToolbar(editor: Editor, config: TipTapConfig): RenderedToolbar {
  const groups = config.toolbar ?? DEFAULT_TOOLBAR;
  const toolbar = document.createElement("div");
  toolbar.className = "django-tiptap__toolbar";
  toolbar.setAttribute("role", "toolbar");

  const wired: Array<{ el: HTMLButtonElement; spec: ButtonSpec }> = [];

  for (const group of groups) {
    const groupEl = document.createElement("div");
    groupEl.className = "django-tiptap__group";
    for (const key of group) {
      const spec = getButton(key);
      if (!spec) {
        console.error(`[DjangoTipTap] unknown toolbar button "${key}"`);
        continue;
      }
      const button = document.createElement("button");
      button.type = "button";
      button.className = "django-tiptap__btn";
      button.innerHTML = spec.icon;
      button.title = spec.title;
      button.setAttribute("aria-label", spec.title);
      button.setAttribute("data-key", key);
      // Keep the editor selection when the button is pressed.
      button.addEventListener("mousedown", (event) => event.preventDefault());
      button.addEventListener("click", (event) => {
        event.preventDefault();
        spec.onClick(editor);
      });
      groupEl.appendChild(button);
      wired.push({ el: button, spec });
    }
    if (groupEl.childElementCount > 0) {
      toolbar.appendChild(groupEl);
    }
  }

  function refresh(): void {
    for (const { el, spec } of wired) {
      if (spec.isActive) {
        el.classList.toggle("is-active", spec.isActive(editor));
      }
      if (spec.isEnabled) {
        el.toggleAttribute("disabled", !spec.isEnabled(editor));
      }
    }
  }

  return { el: toolbar, refresh };
}
