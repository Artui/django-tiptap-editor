// Resolves the editor's extension array: the always-on fidelity baseline plus
// any consumer-registered custom extensions named in config.extensions. Names
// that the baseline already provides are skipped; unknown, unregistered names
// fail loudly in the console.
import type { AnyExtension } from "@tiptap/core";

import { DEFAULT_EXTENSIONS, DEFAULT_LINK_PROTOCOLS } from "./default-config";
import type { TipTapConfig } from "./default-config";
import { BackgroundColor } from "./extensions/background-color";
import { BlockStyle } from "./extensions/block-style";
import { EnterKey } from "./extensions/enter-key";
import { FontSize } from "./extensions/font-size";
import { InlineImage } from "./extensions/inline-image";
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
const BUILTIN_NAMES = new Set<string>([
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

export function buildExtensions(config: TipTapConfig, ctx: ExtensionContext): AnyExtension[] {
  const protocols = config.linkProtocols ?? DEFAULT_LINK_PROTOCOLS;

  const baseline: AnyExtension[] = [
    // StarterKit v2 covers the structural core (document/paragraph/text/bold/
    // italic/strike/code/heading/lists/blockquote/hr/hardBreak/history/cursors).
    // It does NOT include Underline/TextStyle/Link/Image/Table/etc., so the
    // feature extensions below add no duplicates.
    StarterKit,
    // High-priority Enter/Shift-Enter override; "paragraph" (default) adds no
    // bindings, so it's a no-op unless config.enterKey opts into another mode.
    EnterKey.configure({ mode: config.enterKey ?? "paragraph" }),
    BlockStyle,
    Underline,
    TextStyle,
    FontFamily,
    Color,
    BackgroundColor,
    FontSize,
    TextAlign.configure({ types: ["paragraph", "heading"] }),
    Link.configure({
      openOnClick: false,
      autolink: false,
      protocols,
      HTMLAttributes: { target: null, rel: null },
    }),
    InlineImage.configure({ inline: true }),
    Table.configure({ resizable: false }),
    TableRow,
    TableHeader,
    TableCell,
    Subscript,
    Superscript,
    CharacterCount,
  ];

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
