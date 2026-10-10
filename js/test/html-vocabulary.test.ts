// What the editor can emit must be what the server keeps.
//
// The server sanitises every saved value against EXTENSION_HTML_VOCABULARY in
// constants.py, which states the tags, attributes and style properties the
// built-in extensions emit. Only the editor knows whether that statement is
// true, and a Tiptap upgrade can make it false without any Python file
// changing: Tiptap 3 began parsing and rendering a link `title` and table-cell
// alignment, so the editor showed both and every save stripped them. Nothing
// failed, because the server's own tests enumerate the server's table.
//
// This reads the vocabulary from a fixture that scripts/dump_html_vocabulary.py
// writes and tests/test_js_vocabulary_mirror.py keeps current, then renders
// every attribute the editor's schema defines, and every corpus case, and
// asserts that nothing lands outside it.
//
// getHTMLFromFragment comes straight from @tiptap/core: the runtime seam is for
// what the glue ships, and this serialises single nodes, which the glue never
// does.
import { getHTMLFromFragment } from "@tiptap/core";
import { beforeAll, describe, expect, it } from "vitest";

import type { TipTapConfig } from "../src/default-config";
import { BUILTIN_NAMES, buildExtensions } from "../src/build-extensions";
import { FEATURE_CORE, resolveFeatures } from "../src/features";
import { Editor } from "../src/tiptap-runtime";
import corpus from "./fixtures/fidelity-corpus.json";
import vocabularyFixture from "./fixtures/html-vocabulary.json";

type Tags = Record<string, { attributes: string[]; styles: string[] }>;
type Vocabulary = {
  extensions: string[];
  tags: Tags;
  byExtension: Record<string, Tags>;
  decorating: string[];
  documentFeatures: Record<string, string>;
};
const VOCABULARY = vocabularyFixture as Vocabulary;

// One value per schema attribute, chosen so that attribute's renderHTML emits
// something. Every attribute the schema defines must have one: an upgrade that
// adds an attribute fails the completeness test below until someone decides
// what it renders and whether the server should keep it.
const SAMPLES: Record<string, unknown> = {
  ...Object.fromEntries(
    ["paragraph", "heading"].flatMap((type) => [
      [`${type}.margin`, "10px"],
      [`${type}.marginBlockEnd`, "4px"],
      [`${type}.paddingLeft`, "30px"],
      [`${type}.textAlign`, "center"],
    ]),
  ),
  "heading.level": 2,
  "codeBlock.language": "python",
  "orderedList.start": 3,
  "orderedList.type": "a",
  "image.src": "https://example.test/i.png",
  "image.alt": "alt",
  "image.title": "t",
  "image.width": "300",
  "image.height": "200",
  // A passthrough: InlineImage renders whatever style it parsed, so the editor
  // can show any property here while the server keeps IMAGE_STYLE_PROPERTIES.
  // That gap predates this test; the sample is the float and margin the
  // corpus's real images carry.
  "image.style": "float: left; margin: 4px",
  ...Object.fromEntries(
    ["tableCell", "tableHeader"].flatMap((type) => [
      [`${type}.colspan`, 2],
      [`${type}.rowspan`, 2],
      [`${type}.colwidth`, [120]],
      [`${type}.align`, "right"],
    ]),
  ),
  "link.href": "https://example.test/",
  "link.target": "_blank",
  "link.rel": "noopener",
  "link.class": "cta",
  "link.title": "t",
  "textStyle.fontFamily": "Georgia",
  "textStyle.color": "#ff0000",
  "textStyle.backgroundColor": "#00ff00",
  "textStyle.fontSize": "18px",
};

// Flatten rendered HTML into `tag`, `tag[attribute]` and `tag{style-property}`
// entries. Style is read from the attribute text rather than el.style, which
// would expand a `margin` shorthand into four longhands the vocabulary does
// not name.
//
// Parsed in a <template>, not a <div>: a cell rendered on its own is a bare
// <td>, which the HTML parser silently drops outside table context. Parsed in
// a <div>, this test could not see cell alignment at all.
function emitted(html: string): string[] {
  const root = document.createElement("template");
  root.innerHTML = html;
  const entries: string[] = [];
  for (const el of Array.from(root.content.querySelectorAll("*"))) {
    const tag = el.tagName.toLowerCase();
    entries.push(tag);
    for (const name of el.getAttributeNames()) {
      if (name !== "style") {
        entries.push(`${tag}[${name}]`);
        continue;
      }
      for (const declaration of (el.getAttribute("style") ?? "").split(";")) {
        const property = declaration.split(":")[0].trim().toLowerCase();
        if (property) {
          entries.push(`${tag}{${property}}`);
        }
      }
    }
  }
  return entries;
}

function outsideVocabulary(entries: string[], tags: Tags = VOCABULARY.tags): string[] {
  return entries.filter((entry) => {
    const [, tag, attribute, style] = /^([a-z0-9]+)(?:\[(.+)\]|\{(.+)\})?$/.exec(entry) ?? [];
    const spec = tags[tag];
    if (!spec) {
      return true;
    }
    if (attribute) {
      return !spec.attributes.includes(attribute);
    }
    return style ? !spec.styles.includes(style) : false;
  });
}

function makeEditor(config: TipTapConfig): Editor {
  return new Editor({
    element: document.createElement("div"),
    content: "",
    extensions: buildExtensions(config, { tiptap: {}, locale: "en", t: (k) => k }),
  });
}

// Render one node or mark, alone, through the editor's own serializer.
function render(
  editor: Editor,
  kind: "node" | "mark",
  name: string,
  attrs: Record<string, unknown>,
): string {
  const { schema } = editor;
  const node =
    kind === "node"
      ? schema.nodes[name].createAndFill(attrs)
      : schema.nodes.paragraph.create(null, schema.text("x", [schema.marks[name].create(attrs)]));
  return node ? getHTMLFromFragment(schema.topNodeType.create(null, node).content, schema) : "";
}

function attributes(editor: Editor): [kind: "node" | "mark", name: string, attr: string | null][] {
  const { schema } = editor;
  const rows: [kind: "node" | "mark", name: string, attr: string | null][] = [];
  for (const [kind, types] of [
    ["node", schema.nodes],
    ["mark", schema.marks],
  ] as const) {
    for (const [name, type] of Object.entries(types)) {
      if (name === "doc" || name === "text") {
        continue;
      }
      rows.push([kind, name, null]);
      for (const attr of Object.keys(type.spec.attrs ?? {})) {
        rows.push([kind, name, attr]);
      }
    }
  }
  return rows;
}

// Every attribute sample rendered alone, then every corpus case loaded and
// serialised, each flattened to the entries that land outside `tags`.
function emittedOutside(editor: Editor, tags: Tags): string[] {
  const outside: string[] = [];
  for (const [kind, name, attr] of attributes(editor)) {
    const html = render(editor, kind, name, attr ? { [attr]: SAMPLES[`${name}.${attr}`] } : {});
    // An attribute that renders nothing is a sample that proves nothing.
    expect(html, `${name}.${attr} rendered nothing`).not.toBe("");
    for (const entry of outsideVocabulary(emitted(html), tags)) {
      outside.push(`${name}${attr ? `.${attr}` : ""} -> ${entry}`);
    }
  }
  for (const fx of corpus.results) {
    editor.commands.setContent(fx.output, { emitUpdate: false });
    for (const entry of outsideVocabulary(emitted(editor.getHTML()), tags)) {
      outside.push(`${fx.id} -> ${entry}`);
    }
  }
  return outside;
}

describe("the editor emits only what the server keeps", () => {
  let editor: Editor;

  beforeAll(() => {
    editor = makeEditor({});
  });

  it("has a sample for every attribute the schema defines, and no stale ones", () => {
    const defined = attributes(editor)
      .filter(([, , attr]) => attr !== null)
      .map(([, name, attr]) => `${name}.${attr}`);
    expect(defined.filter((key) => !(key in SAMPLES))).toEqual([]);
    expect(Object.keys(SAMPLES).filter((key) => !defined.includes(key))).toEqual([]);
  });

  it("renders every node and mark attribute inside the vocabulary", () => {
    const outside: string[] = [];
    for (const [kind, name, attr] of attributes(editor)) {
      const html = render(editor, kind, name, attr ? { [attr]: SAMPLES[`${name}.${attr}`] } : {});
      // An attribute that renders nothing is a sample that proves nothing.
      expect(html, `${name}.${attr} rendered nothing`).not.toBe("");
      for (const entry of outsideVocabulary(emitted(html))) {
        outside.push(`${name}${attr ? `.${attr}` : ""} -> ${entry}`);
      }
    }
    expect(outside).toEqual([]);
  });

  it("renders every corpus case inside the vocabulary", () => {
    const outside: string[] = [];
    for (const fx of corpus.results) {
      editor.commands.setContent(fx.output, { emitUpdate: false });
      for (const entry of outsideVocabulary(emitted(editor.getHTML()))) {
        outside.push(`${fx.id} -> ${entry}`);
      }
    }
    expect(outside).toEqual([]);
  });

  it("knows the same built-in extension names as the server", () => {
    expect([...BUILTIN_NAMES].sort()).toEqual(VOCABULARY.extensions);
  });

  it("has a document-table entry for every node and mark type the schema defines", () => {
    // The server narrows a stored JSON document by DOCUMENT_FEATURES; a type
    // missing from it would be unwrapped on every restricted field.
    const { schema } = editor;
    const types = [...Object.keys(schema.nodes), ...Object.keys(schema.marks)];
    expect(types.filter((name) => !(name in VOCABULARY.documentFeatures))).toEqual([]);
  });
});

// The allowlist a restricted field is cleaned against, restated from the fixture
// the way get_html_schema builds it: tags from every resolved feature but the
// decorating ones, then each resolved feature's attributes and styles onto the
// tags that made it.
function narrowedTags(resolved: Set<string>): Tags {
  const tags: Tags = {};
  for (const decorating of [false, true]) {
    for (const name of resolved) {
      if (VOCABULARY.decorating.includes(name) !== decorating) {
        continue;
      }
      for (const [tag, spec] of Object.entries(VOCABULARY.byExtension[name] ?? {})) {
        if (decorating && !(tag in tags)) {
          continue;
        }
        tags[tag] ??= { attributes: [], styles: [] };
        tags[tag].attributes.push(...spec.attributes);
        tags[tag].styles.push(...spec.styles);
      }
    }
  }
  return tags;
}

const SINGLE_FEATURES = VOCABULARY.extensions.filter((name) => !FEATURE_CORE.has(name));

describe("a restricted editor emits only what its field keeps", () => {
  // One editor per feature, alone with the core, and the core alone. A server
  // that narrows a field to its features and an editor that mounts them are two
  // statements of one set; this is where they are compared.
  it.each([[[] as string[]], ...SINGLE_FEATURES.map((name) => [[name]])])(
    "features: %j",
    (features) => {
      const config: TipTapConfig = { features };
      const resolved = resolveFeatures(config) as Set<string>;
      const editor = makeEditor(config);
      expect(emittedOutside(editor, narrowedTags(resolved))).toEqual([]);

      // And the document side: every type and owned attribute in this editor's
      // schema belongs to a resolved feature, and every table entry for a
      // resolved feature is one this editor actually defines.
      const { schema } = editor;
      const table = VOCABULARY.documentFeatures;
      const defined = new Set<string>();
      for (const types of [schema.nodes, schema.marks]) {
        for (const [name, type] of Object.entries(types)) {
          defined.add(name);
          for (const attr of Object.keys(type.spec.attrs ?? {})) {
            defined.add(`${name}.${attr}`);
          }
        }
      }
      const unowned = [...defined].filter((key) => key in table && !resolved.has(table[key]));
      expect(unowned).toEqual([]);
      const expected = Object.keys(table).filter((key) => {
        const owner = key.split(".")[0];
        return resolved.has(table[key]) && resolved.has(table[owner]);
      });
      expect(expected.filter((key) => !defined.has(key))).toEqual([]);
    },
  );
});
