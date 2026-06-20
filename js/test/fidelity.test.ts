// The schema's test of record. Feeds real TinyMCE output (the committed corpus)
// through the production extension set and asserts no content loss. Locks in the
// round-trip fidelity so future extension changes can't silently regress it.
import { beforeAll, describe, expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import { Editor } from "../src/tiptap-runtime";
import { canonicalLoose, textOf } from "./canonical";
import corpus from "./fixtures/tinymce-corpus.json";

// Documented, content-preserving normalizations: text is intact, markup differs
// in a defined way. If one of these starts round-tripping exactly, the test
// fails on purpose — remove it here (fidelity improved).
const NORMALIZED: Record<string, string> = {
  "table-basic": "TipTap table adds colgroup/min-width/colspan/rowspan + <p> in cells",
  "table-styled": "table/cell layout normalized; colspan + content preserved",
  "messy-divs": "<div> mapped to <p> (no div node in the default schema)",
  "messy-style-attr": "block-level text color on <p> dropped (rare); bold preserved",
  "cmd-underline": "underline kept as <u> + a leftover empty <span>",
  "cmd-bold-then-italic": "mark nesting order (<em><strong> vs <strong><em>)",
  "link-javascript": "empty stripped-href <a> dropped entirely (security)",
};

describe("TinyMCE corpus round-trip", () => {
  let editor: Editor;

  beforeAll(() => {
    const el = document.createElement("div");
    document.body.appendChild(el);
    editor = new Editor({
      element: el,
      content: "",
      extensions: buildExtensions({}, { tiptap: {}, locale: "en", t: (k) => k }),
    });
  });

  for (const fx of corpus.results) {
    it(`preserves content: ${fx.id}`, () => {
      editor.commands.setContent(fx.output, false);
      const out = editor.getHTML();

      // No visible-text loss for ANY fixture.
      expect(textOf(out), `text drift in ${fx.id}\n  out: ${out}`).toBe(textOf(fx.output));

      const equal = canonicalLoose(out) === canonicalLoose(fx.output);
      if (fx.id in NORMALIZED) {
        expect(
          equal,
          `${fx.id} now round-trips exactly — remove it from NORMALIZED`,
        ).toBe(false);
      } else {
        expect(
          equal,
          `round-trip drift in ${fx.id}\n  in:  ${fx.output}\n  out: ${out}`,
        ).toBe(true);
      }
    });
  }
});
