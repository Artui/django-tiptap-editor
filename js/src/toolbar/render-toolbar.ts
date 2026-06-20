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

function renderButton(key: string, spec: ButtonSpec, onClick: () => void): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "django-tiptap__btn";
  button.innerHTML = spec.icon ?? "";
  button.title = spec.title;
  button.setAttribute("aria-label", spec.title);
  button.setAttribute("data-key", key);
  // Keep the editor selection when the button is pressed.
  button.addEventListener("mousedown", (event) => event.preventDefault());
  button.addEventListener("click", (event) => {
    event.preventDefault();
    onClick();
  });
  return button;
}

export function renderToolbar(editor: Editor, config: TipTapConfig): RenderedToolbar {
  const groups = config.toolbar ?? DEFAULT_TOOLBAR;
  const toolbar = document.createElement("div");
  toolbar.className = "django-tiptap__toolbar";
  toolbar.setAttribute("role", "toolbar");

  const refreshers: Array<() => void> = [];

  for (const group of groups) {
    const groupEl = document.createElement("div");
    groupEl.className = "django-tiptap__group";
    for (const key of group) {
      const spec = getButton(key);
      if (!spec) {
        console.error(`[DjangoTipTap] unknown toolbar button "${key}"`);
        continue;
      }
      if (spec.render) {
        const control = spec.render(editor);
        control.el.setAttribute("data-key", key);
        groupEl.appendChild(control.el);
        if (control.refresh) {
          refreshers.push(control.refresh);
        }
        continue;
      }
      if (!spec.icon || !spec.onClick) {
        console.error(`[DjangoTipTap] toolbar button "${key}" needs an icon + onClick (or render)`);
        continue;
      }
      const onClick = spec.onClick;
      // Refresh after the command runs: most commands fire a transaction (which
      // refreshes anyway), but some — e.g. source-view's setEditable — don't.
      const button = renderButton(key, spec, () => {
        onClick(editor);
        refresh();
      });
      groupEl.appendChild(button);
      refreshers.push(() => {
        if (spec.isActive) {
          button.classList.toggle("is-active", spec.isActive(editor));
        }
        if (spec.isEnabled) {
          button.toggleAttribute("disabled", !spec.isEnabled(editor));
        }
      });
    }
    if (groupEl.childElementCount > 0) {
      toolbar.appendChild(groupEl);
    }
  }

  function refresh(): void {
    for (const r of refreshers) {
      r();
    }
  }

  return { el: toolbar, refresh };
}
