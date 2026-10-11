// Resolves the editor's extension array: the fidelity baseline plus any
// consumer-registered custom extensions named in config.extensions. The baseline
// is every built-in unless config.features restricts it (see features.ts). Names
// that the baseline already provides are skipped; unknown, unregistered names
// fail loudly in the console.
import type { AnyExtension } from "@tiptap/core";

import { DEFAULT_EXTENSIONS, DEFAULT_LINK_PROTOCOLS } from "./default-config";
import type { TipTapConfig } from "./default-config";
import { BackgroundColor } from "./extensions/background-color";
import { BlockStyle } from "./extensions/block-style";
import { EnterKey } from "./extensions/enter-key";
import { FontSize } from "./extensions/font-size";
import { ImageResize } from "./extensions/image-resize";
import { InlineImage } from "./extensions/inline-image";
import { resolveFeatures } from "./features";
import { getExtensionFactory } from "./registry";
import type { ExtensionContext } from "./registry";
import {
  CharacterCount,
  Color,
  FontFamily,
  Link,
  StarterKit,
  Subscript,
  Superscript,
  Table,
  TableCell,
  TableHeader,
  TableRow,
  TextAlign,
  TextStyle,
  Underline,
} from "./tiptap-runtime";

// Config names the always-on baseline already covers — the registry treats them
// as known no-ops so consumers don't get spurious "unknown extension" warnings.
// The server's EXTENSION_HTML_VOCABULARY is keyed by the same names, and
// test/html-vocabulary.test.ts holds the two lists equal.
export const BUILTIN_NAMES: ReadonlySet<string> = new Set<string>([
  "document",
  "text",
  "paragraph",
  "bold",
  "italic",
  "strike",
  "code",
  "codeBlock",
  "heading",
  "bulletList",
  "orderedList",
  "listItem",
  "blockquote",
  "horizontalRule",
  "hardBreak",
  "history",
  "dropcursor",
  "gapcursor",
  "underline",
  "textStyle",
  "fontFamily",
  "color",
  "backgroundColor",
  "highlight",
  "fontSize",
  "textAlign",
  "link",
  "image",
  "table",
  "tableRow",
  "tableCell",
  "tableHeader",
  "subscript",
  "superscript",
  "characterCount",
  "sourceView",
]);

// StarterKit's children that are features a field can leave out, keyed by
// StarterKit option name (which matches the feature name for each of these).
// The core children (document, text, paragraph, hardBreak, undoRedo, the two
// cursors) are never switched off, and link / underline / trailingNode are off
// in every editor already (see below).
const STARTER_KIT_FEATURES = [
  "bold",
  "italic",
  "strike",
  "code",
  "codeBlock",
  "heading",
  "bulletList",
  "orderedList",
  "listItem",
  "blockquote",
  "horizontalRule",
] as const;

// The StarterKit options for a restricted field: every excluded child false.
// ListKeymap goes with listItem; its handlers already bail out without the node,
// but a keymap for a list the field cannot hold is noise in the extension set.
function restrictedStarterKit(enabled: (name: string) => boolean): Record<string, false> {
  const off: Record<string, false> = {};
  for (const name of STARTER_KIT_FEATURES) {
    if (!enabled(name)) {
      off[name] = false;
    }
  }
  if (!enabled("listItem")) {
    off.listKeymap = false;
  }
  return off;
}

export function buildExtensions(config: TipTapConfig, ctx: ExtensionContext): AnyExtension[] {
  const protocols = config.linkProtocols ?? DEFAULT_LINK_PROTOCOLS;
  // null is unrestricted: every check below passes and every option comes out
  // as it was before `features` existed, so the array is the same one, in the
  // same order. That order is what decides how marks nest in getHTML(), and the
  // fidelity corpus pins it.
  const allowed = resolveFeatures(config);
  const enabled = (name: string): boolean => allowed === null || allowed.has(name);
  // Node types the block-level attributes decorate. A type the schema lacks
  // would only carry an attribute nothing renders, but setTextAlign walks this
  // list, so it names exactly the nodes that exist.
  const blockTypes = enabled("heading") ? ["paragraph", "heading"] : ["paragraph"];

  // Each entry is mounted only when its feature is, so an excluded node or mark
  // is not in the schema at all: no input rule, shortcut, paste or command can
  // produce it. Pasted markup for one keeps its text, as for any unknown tag.
  const gated: Array<[boolean, AnyExtension]> = [
    // StarterKit v3 covers the structural core (document/paragraph/text/bold/
    // italic/strike/code/heading/lists/blockquote/hr/hardBreak/undoRedo/cursors)
    // and also bundles Link, Underline, ListKeymap and TrailingNode. Link and
    // Underline are switched off because the configured ones below replace them
    // (two registrations of one name is a tiptap warning and an undefined
    // winner). TrailingNode appends an empty <p> after a doc ending in a list,
    // heading or blockquote, which breaks byte-identical round trips. ListKeymap
    // stays on: it is keyboard behaviour only (Backspace at the start of a list
    // item lifts it, Delete at the end joins the next one), with no schema or
    // markup of its own, so stored values are unchanged. A restricted field
    // switches off each child it excludes (see restrictedStarterKit).
    [
      true,
      StarterKit.configure({
        link: false,
        underline: false,
        trailingNode: false,
        ...restrictedStarterKit(enabled),
      }),
    ],
    // High-priority Enter/Shift-Enter override; "paragraph" (default) adds no
    // bindings, so it's a no-op unless config.enterKey opts into another mode.
    [true, EnterKey.configure({ mode: config.enterKey ?? "paragraph" })],
    // Margins on paragraphs always, and on headings where headings exist.
    [true, enabled("heading") ? BlockStyle : BlockStyle.configure({ types: blockTypes })],
    [enabled("underline"), Underline],
    [enabled("textStyle"), TextStyle],
    [enabled("fontFamily"), FontFamily],
    [enabled("color"), Color],
    // `highlight` is this attribute under its toolbar name, and resolves to it.
    [enabled("backgroundColor"), BackgroundColor],
    [enabled("fontSize"), FontSize],
    [enabled("textAlign"), TextAlign.configure({ types: blockTypes })],
    [
      enabled("link"),
      Link.configure({
        openOnClick: false,
        autolink: false,
        protocols,
        HTMLAttributes: { target: null, rel: null },
      }),
    ],
    [enabled("image"), InlineImage.configure({ inline: true })],
    // Rows, cells and headers mount with the table (which always resolves all
    // three) and never alone: a row whose content names a cell type the schema
    // lacks is a schema error that stops the editor mounting, and none of the
    // three means anything outside a table.
    [enabled("table"), Table.configure({ resizable: false })],
    [enabled("table"), TableRow],
    [enabled("table"), TableHeader],
    [enabled("table"), TableCell],
    [enabled("subscript"), Subscript],
    [enabled("superscript"), Superscript],
    [enabled("characterCount"), CharacterCount],
    // Editing chrome, not schema: the image node is identical either way, so
    // turning this off changes nothing about the stored value. Without the
    // image node there is nothing to resize ("features: [] mounts the core
    // alone" in test/restrict-features.test.ts holds that clause).
    [enabled("image") && config.imageResize !== false, ImageResize],
  ];
  const baseline = gated.filter(([on]) => on).map(([, ext]) => ext);

  const requested = config.extensions ?? DEFAULT_EXTENSIONS;
  const custom: AnyExtension[] = [];
  const seen = new Set<string>();
  for (const name of requested) {
    if (BUILTIN_NAMES.has(name)) {
      continue;
    }
    const factory = getExtensionFactory(name);
    if (!factory) {
      console.error(
        `[DjangoTipTap] unknown extension "${name}" — not a built-in and not registered via registerExtension()`,
      );
      continue;
    }
    const produced = factory(config, ctx);
    for (const ext of Array.isArray(produced) ? produced : [produced]) {
      const exName = ext?.name ?? "";
      if (exName && seen.has(exName)) {
        continue;
      }
      if (exName) {
        seen.add(exName);
      }
      custom.push(ext);
    }
  }

  return [...baseline, ...custom];
}
