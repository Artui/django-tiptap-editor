// Builds the toolbar DOM for an editor and returns a refresh() that syncs every
// button's active / enabled state. Buttons preserve the editor selection on
// click (mousedown preventDefault) so commands apply to the current range.
import { DEFAULT_TOOLBAR } from "../default-config";
import type { TipTapConfig } from "../default-config";
import { featureEnabled, resolveFeatures } from "../features";
import { translatorFor } from "../i18n";
import type { Editor } from "../tiptap-runtime";
import { getButton } from "./button-registry";
import type { ButtonSpec, RenderedControl } from "./button-registry";
import { applyLabel, toolbarLabel } from "./label";
import { isLocked } from "./lock";

export interface RenderedToolbar {
  el: HTMLElement;
  refresh: () => void;
}

function renderButton(
  key: string,
  spec: ButtonSpec,
  title: string,
  label: string | undefined,
  onClick: () => void,
): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "django-tiptap__btn";
  button.innerHTML = spec.icon ?? "";
  button.title = title;
  button.setAttribute("aria-label", title);
  if (label) {
    applyLabel(button, label);
  }
  button.setAttribute("data-key", key);
  // Keep the editor selection when the button is pressed.
  button.addEventListener("mousedown", (event) => event.preventDefault());
  button.addEventListener("click", (event) => {
    event.preventDefault();
    onClick();
  });
  return button;
}

const FORM_CONTROLS = "button, input, select, textarea";

// Frees only what it disabled; "re-enables only what the lock disabled" fails without a conjunct.
function lockingRefresh(editor: Editor, control: RenderedControl): () => void {
  const held = new Set<Element>();
  return () => {
    if (!isLocked(editor)) {
      held.forEach((node) => node.removeAttribute("disabled"));
      held.clear();
    }
    control.refresh?.();
    if (isLocked(editor)) {
      const nodes = [control.el, ...Array.from(control.el.querySelectorAll(FORM_CONTROLS))];
      for (const node of nodes) {
        if (node.matches(FORM_CONTROLS) && !node.hasAttribute("disabled")) {
          node.setAttribute("disabled", "");
          held.add(node);
        }
      }
    }
  };
}

export function renderToolbar(editor: Editor, config: TipTapConfig): RenderedToolbar {
  const groups = config.toolbar ?? DEFAULT_TOOLBAR;
  const t = translatorFor(editor);
  // A control whose feature this field leaves out has no command behind it, and
  // clicking it would throw. Read from the same resolver buildExtensions mounts
  // from, rather than by probing the editor, because not every feature is
  // something the editor can be asked about: sourceView is chrome with no
  // extension, and fontSize / backgroundColor are attributes with no command.
  const features = resolveFeatures(config);
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
      if (!featureEnabled(features, spec.requires)) {
        // The default toolbar is everything, so trimming it to the field is
        // expected; a toolbar the config spelled out disagrees with its own
        // feature list, which is worth saying once, at render, not per refresh.
        if (config.toolbar) {
          console.warn(
            `[DjangoTipTap] toolbar button "${key}" hidden — it needs the "${spec.requires}" feature, which this field's features leave out`,
          );
        }
        continue;
      }
      if (spec.render) {
        const control = spec.render(editor);
        control.el.setAttribute("data-key", key);
        groupEl.appendChild(control.el);
        refreshers.push(lockingRefresh(editor, control));
        continue;
      }
      if (!spec.icon || !spec.onClick) {
        console.error(`[DjangoTipTap] toolbar button "${key}" needs an icon + onClick (or render)`);
        continue;
      }
      const onClick = spec.onClick;
      // Refresh after the command runs: most commands fire a transaction (which
      // refreshes anyway), but some — e.g. source-view's setEditable — don't.
      const button = renderButton(key, spec, t(spec.title), toolbarLabel(config, key), () => {
        onClick(editor);
        refresh();
      });
      groupEl.appendChild(button);
      refreshers.push(() => {
        if (spec.isActive) {
          const active = spec.isActive(editor);
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-pressed", String(active));
        }
        const enabled = spec.isEnabled ? spec.isEnabled(editor) : true;
        button.toggleAttribute("disabled", isLocked(editor) || !enabled);
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
