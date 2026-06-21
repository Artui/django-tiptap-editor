// HTML <-> ProseMirror-JSON conversion against the package's exact extension
// set. These run in the browser (the bundle), so a pip-only consumer gets a
// faithful converter without Node — the basis for the HTML->JSON migration path
// and for rendering JSON-stored content client-side (SPA / dynamic display).
import { buildExtensions } from "./build-extensions";
import type { TipTapConfig } from "./default-config";
import { getTranslator } from "./i18n";
import { generateHTML, generateJSON } from "./tiptap-runtime";

function extensionsFor(config: TipTapConfig) {
  const locale = config.locale ?? "en";
  return buildExtensions(config, { tiptap: {}, locale, t: getTranslator(locale) });
}

// Parse HTML into a ProseMirror document (the schema drops anything it can't
// model — same normalization the editor applies on load).
export function htmlToJSON(html: string, config: TipTapConfig = {}): object {
  return generateJSON(html, extensionsFor(config));
}

// Render a ProseMirror document back to an HTML string.
export function renderHTML(doc: object, config: TipTapConfig = {}): string {
  return generateHTML(doc, extensionsFor(config));
}

// Convert HTML into the {doc, html} envelope TipTapJSONField stores. The mirror
// is the schema's re-render of the parsed doc (normalized), not the raw input.
export function htmlToStored(
  html: string,
  config: TipTapConfig = {},
): { doc: object; html: string } {
  const exts = extensionsFor(config);
  const doc = generateJSON(html, exts);
  return { doc, html: generateHTML(doc, exts) };
}
