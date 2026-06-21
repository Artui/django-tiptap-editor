// Theming tiers 2 & 3 — region + shell renderers (semi-stable / experimental).
//
// Tier 1 (design tokens + the button registry) lives in ui.ts; this module is
// the next two tiers down the stability ladder:
//
//   Tier 2 — region renderers. ui.setRenderer(region, fn) replaces ONE region.
//            The chrome regions (toolbar / statusbar) are laid out by the shell;
//            the floating regions (bubbleMenu / floatingMenu) are selection-
//            anchored overlays positioned over the editor. fn(ctx) returns a DOM
//            node that IS the region (a full replacement, not a wrapper).
//   Tier 3 — shell renderer. ui.setShellRenderer(fn) hands the consumer the
//            whole editor shell; fn(ctx) returns the shell root and must place
//            ctx.content (the ProseMirror host) somewhere inside it.
//
// Renderers are module-global and must be registered BEFORE auto-mount, exactly
// like extensions and buttons (see the load-order note in the docs).
import type { TipTapConfig } from "./default-config";
import type { Translator } from "./i18n";
import type { Editor } from "./tiptap-runtime";
import { getButton } from "./toolbar/button-registry";
import type { ButtonSpec } from "./toolbar/button-registry";

// Chrome regions (laid out by the shell) and floating regions (selection-
// anchored overlays). bubbleMenu shows for a non-empty selection; floatingMenu
// shows on an empty text line.
export type ChromeRegion = "toolbar" | "statusbar";
export type FloatingRegion = "bubbleMenu" | "floatingMenu";
export type Region = ChromeRegion | FloatingRegion;

const ALL_REGIONS = new Set<Region>(["toolbar", "statusbar", "bubbleMenu", "floatingMenu"]);
export const FLOATING_REGIONS: readonly FloatingRegion[] = ["bubbleMenu", "floatingMenu"];

// Passed to a region renderer. Exposes the editor, its config, the active
// translator, and a resolver for registered toolbar buttons so a custom region
// can reuse built-in controls.
export interface RegionContext {
  editor: Editor;
  config: TipTapConfig;
  t: Translator;
  getButton: (key: string) => ButtonSpec | undefined;
}

// Passed to the shell renderer. Adds `content` — the ProseMirror host element the
// consumer MUST insert somewhere into the returned shell, or the editor is
// invisible.
export interface ShellContext extends RegionContext {
  content: HTMLElement;
}

export type RegionRenderer = (ctx: RegionContext) => HTMLElement;
export type ShellRenderer = (ctx: ShellContext) => HTMLElement;

const regionRenderers = new Map<Region, RegionRenderer>();
let shellRenderer: ShellRenderer | null = null;

export function setRenderer(region: string, fn: RegionRenderer): void {
  if (!ALL_REGIONS.has(region as Region)) {
    console.error(
      `[DjangoTipTap] ui.setRenderer: unknown region "${region}" ` +
        '(expected "toolbar" | "statusbar" | "bubbleMenu" | "floatingMenu").',
    );
    return;
  }
  regionRenderers.set(region as Region, fn);
}

export function getRenderer(region: Region): RegionRenderer | undefined {
  return regionRenderers.get(region);
}

export function setShellRenderer(fn: ShellRenderer): void {
  shellRenderer = fn;
}

export function getShellRenderer(): ShellRenderer | null {
  return shellRenderer;
}

// Builds the RegionContext shared by region and shell renderers.
export function rendererContext(editor: Editor, config: TipTapConfig, t: Translator): RegionContext {
  return { editor, config, t, getButton };
}
