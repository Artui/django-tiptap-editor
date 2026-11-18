// toolbarLabels: a text label beside a toolbar control's glyph, read per editor
// from its config (a built-in dropdown's title doubles as its toolbar key). The
// label is used verbatim, never through t(), and "" counts as absent.
import type { TipTapConfig } from "../default-config";

export function toolbarLabel(config: TipTapConfig, key: string): string | undefined {
  return config.toolbarLabels?.[key] || undefined;
}

// Names the button by its label (WCAG 2.5.3) and shows it after the glyph and
// before a trigger's caret, as text, so a label can never inject markup.
export function applyLabel(button: HTMLButtonElement, label: string): void {
  const span = document.createElement("span");
  span.className = "django-tiptap__btn-label";
  span.textContent = label;
  button.classList.add("django-tiptap__btn--labelled");
  button.insertBefore(span, button.querySelector(":scope > .django-tiptap__caret"));
  button.title = label;
  button.setAttribute("aria-label", label);
}
