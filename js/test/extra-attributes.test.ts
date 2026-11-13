// config.extraAttributes against the server's table: every type and attribute
// the server lets a grant name is one the editor keeps through a re-parse (the
// source view's path), and nothing outside the table or the field's schema is
// mounted. The table comes from the fixture scripts/dump_html_vocabulary.py writes.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import type { TipTapConfig } from "../src/default-config";
import { EXTRA_ATTRIBUTE_NAMES, EXTRA_ATTRIBUTE_TYPES } from "../src/extensions/extra-attributes";
import DjangoTipTap from "../src/index";
import { Editor } from "../src/tiptap-runtime";
import { toggleSourceView } from "../src/toolbar/source-view";
import vocabularyFixture from "./fixtures/html-vocabulary.json";

const TABLE = vocabularyFixture.extraAttributes as { names: string[]; tags: Record<string, string[]> };
const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };
const FULL_GRANT = Object.fromEntries(Object.keys(TABLE.tags).map((type) => [type, TABLE.names]));

function makeEditor(config: TipTapConfig): Editor {
  const element = document.createElement("div");
  document.body.appendChild(element);
  return new Editor({ element, extensions: buildExtensions(config, ctx) });
}

function roundTrip(config: TipTapConfig, html: string): string {
  const editor = makeEditor(config);
  editor.commands.setContent(html, { emitUpdate: false });
  const out = editor.getHTML();
  editor.destroy();
  return out;
}

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("extraAttributes", () => {
  it("allows the same types and names as the server", () => {
    expect([...EXTRA_ATTRIBUTE_TYPES].sort()).toEqual(Object.keys(TABLE.tags).sort());
    expect([...EXTRA_ATTRIBUTE_NAMES].sort()).toEqual(TABLE.names);
  });

  it("keeps every granted attribute on every tag of every granted type", () => {
    for (const tags of Object.values(TABLE.tags)) {
      for (const tag of tags) {
        for (const name of TABLE.names) {
          const html = `<${tag} ${name}="lead">x</${tag}>`;
          expect(roundTrip({ extraAttributes: FULL_GRANT }, html)).toBe(html);
        }
      }
    }
  });

  it("keeps a class after the block styles, the order render_doc writes", () => {
    const html = '<p style="text-align: center;" class="lead">x</p>';
    expect(roundTrip({ extraAttributes: FULL_GRANT }, html)).toBe(html);
  });

  it("drops a class nothing grants, and grants per type", () => {
    const html = '<p class="lead">x</p><h2 class="t">y</h2>';
    expect(roundTrip({}, html)).toBe("<p>x</p><h2>y</h2>");
    expect(roundTrip({ extraAttributes: { heading: ["class"] } }, html)).toBe(
      '<p>x</p><h2 class="t">y</h2>',
    );
  });

  it("mounts nothing for an unknown type, an unknown name or a type the schema lacks", () => {
    const names = (config: TipTapConfig) =>
      buildExtensions(config, ctx).map((extension) => extension.name);
    expect(names({ extraAttributes: { blockquote: ["class"], paragraph: ["id"] } })).not.toContain(
      "extraAttributes",
    );
    expect(names({ features: ["bold"], extraAttributes: { heading: ["class"] } })).not.toContain(
      "extraAttributes",
    );
    expect(
      roundTrip({ features: ["bold"], extraAttributes: FULL_GRANT }, '<h2 class="t">y</h2>'),
    ).toBe("<p>y</p>");
  });

  it("carries a granted class through the source view into the JSON envelope", () => {
    const form = document.createElement("form");
    const textarea = document.createElement("textarea");
    textarea.id = "extra-json";
    textarea.setAttribute("data-tiptap-storage", "json");
    textarea.value = "";
    form.appendChild(textarea);
    document.body.appendChild(form);
    const editor = DjangoTipTap.init(textarea, { extraAttributes: FULL_GRANT });
    toggleSourceView(editor);
    const source = document.querySelector<HTMLTextAreaElement>("textarea.django-tiptap__source");
    if (!source) {
      throw new Error("source view is not open");
    }
    source.value = '<p class="lead">x</p>';
    source.dispatchEvent(new Event("input", { bubbles: true }));
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    const envelope = JSON.parse(textarea.value);
    expect(envelope.html).toBe('<p class="lead">x</p>');
    expect(envelope.doc.content[0].attrs.class).toBe("lead");
    DjangoTipTap.destroy("extra-json");
  });
});
