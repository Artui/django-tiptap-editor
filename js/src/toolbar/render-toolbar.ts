// Builds the toolbar DOM for an editor and returns a refresh() that syncs every
// button's active / enabled state. Buttons preserve the editor selection on
// click (mousedown preventDefault) so commands apply to the current range.
import { DEFAULT_TOOLBAR } from "../default-config";
import type { TipTapConfig } from "../default-config";
import { resolveFeatures } from "../features";
import { translatorFor } from "../i18n";
import type { Editor } from "../tiptap-runtime";
import { getButton } from "./button-registry";
import type { ButtonSpec } from "./button-registry";

export interface RenderedToolbar {
  el: HTMLElement;
  refresh: () => void;
}

function renderButton(
  key: string,
  spec: ButtonSpec,
  label: string,
  onClick: () => void,
): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "django-tiptap__btn";
  button.innerHTML = spec.icon ?? "";
  button.title = label;
  button.setAttribute("aria-label", label);
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
      if (spec.requires !== undefined && features !== null && !features.has(spec.requires)) {
        // The default toolbar is everything, so trimming it to the field is
        // expected; a toolbar the config spelled out disagrees with its own
        // feature list, which is worth saying once, at render, not per refresh.
        // Each clause has a test in test/restrict-features.test.ts that fails
        // without it: "leaves consumer-registered buttons alone" (requires),
        // "every feature listed / no features key" (null) and "renders none of
        // the excluded buttons by default" (has).
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
      const button = renderButton(key, spec, t(spec.title), () => {
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
