// A field's `features` list decides which extensions exist, not just which
// toolbar buttons show. Each test drives a real route an author has into the
// document (an input rule, a keyboard shortcut, the clipboard, a file drop, the
// toolbar, source view) against a restricted editor, and most pair it with the
// same route on an unrestricted one: that control is what proves the harness
// reaches the route at all, so a green restricted assertion is not vacuous.
//
// Built through buildExtensions and the plain config object, so the file runs
// against any tree whose config accepts unknown keys, which is how it was seen
// failing before `features` was honoured.
import { afterEach, describe, expect, it, vi } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import type { TipTapConfig } from "../src/default-config";
import { setEditorConfig } from "../src/editor-config";
import { rendererContext } from "../src/renderers";
import { getButton, registerButton } from "../src/toolbar/button-registry";
import { registerBuiltInButtons } from "../src/toolbar/built-in-buttons";
import { renderToolbar } from "../src/toolbar/render-toolbar";
import { toggleSourceView } from "../src/toolbar/source-view";
import { Editor } from "../src/tiptap-runtime";
import { insertImage, uploadAndInsert, wireImageDropPaste } from "../src/upload";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };

// The email-style field the bug report describes: inline emphasis, links and
// lists, and nothing that changes the shape or the colour of the text.
const EMAIL: TipTapConfig = { features: ["bold", "italic", "link", "bulletList", "orderedList"] };

function makeEditor(config: TipTapConfig, content = "<p></p>"): Editor {
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({ element, content, extensions: buildExtensions(config, ctx) });
  setEditorConfig(editor, config);
  return editor;
}

// What the browser does for a printable key: offer it to handleTextInput (where
// input rules live) and insert it only when nothing claimed it.
function typeText(editor: Editor, text: string): void {
  const { view } = editor;
  for (const char of text) {
    const { from, to } = view.state.selection;
    const insert = () => view.state.tr.insertText(char, from, to);
    const handled = view.someProp("handleTextInput", (f) => f(view, from, to, char, insert));
    if (!handled) {
      view.dispatch(insert());
    }
  }
}

function pressCtrlAlt2(editor: Editor): void {
  editor.view.dom.dispatchEvent(
    new KeyboardEvent("keydown", {
      key: "2",
      code: "Digit2",
      ctrlKey: true,
      altKey: true,
      bubbles: true,
      cancelable: true,
    }),
  );
}

// The real paste path: ProseMirror's clipboard parser, transformPasted and the
// paste rules, not setContent. jsdom has no ClipboardEvent, so pass a plain one.
function paste(editor: Editor, html: string): void {
  editor.commands.focus("end");
  editor.view.pasteHTML(html, new Event("paste") as ClipboardEvent);
}

function names(editor: Editor): { nodes: string[]; marks: string[]; extensions: string[] } {
  return {
    nodes: Object.keys(editor.schema.nodes).sort(),
    marks: Object.keys(editor.schema.marks).sort(),
    extensions: editor.extensionManager.extensions.map((ext) => ext.name),
  };
}

function toolbarKeys(el: HTMLElement): string[] {
  return Array.from(el.querySelectorAll("[data-key]")).map((b) => b.getAttribute("data-key") ?? "");
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("a restricted field has no route to an excluded feature", () => {
  it("typing `## ` does not create a heading", () => {
    const full = makeEditor({});
    full.commands.focus("end");
    typeText(full, "## Title");
    expect(full.getHTML()).toBe("<h2>Title</h2>");

    const email = makeEditor(EMAIL);
    email.commands.focus("end");
    typeText(email, "## Title");
    expect(email.getHTML()).toBe("<p>## Title</p>");
  });

  it("Ctrl+Alt+2 does not create a heading", () => {
    const full = makeEditor({}, "<p>Title</p>");
    full.commands.focus("end");
    pressCtrlAlt2(full);
    expect(full.getHTML()).toBe("<h2>Title</h2>");

    const email = makeEditor(EMAIL, "<p>Title</p>");
    email.commands.focus("end");
    pressCtrlAlt2(email);
    expect(email.getHTML()).toBe("<p>Title</p>");
  });

  it.each([
    ["a heading", "<h2>Title</h2>", "<h2>", "<p>Title</p>"],
    ["a table", "<table><tbody><tr><td>Cell</td></tr></tbody></table>", "<table", "<p>Cell</p>"],
    ["an image", '<p>a<img src="https://example.com/x.png">b</p>', "<img", "<p>ab</p>"],
    [
      "a coloured, sized span",
      '<p><span style="color: red; font-size: 20px">Tinted</span></p>',
      "<span",
      "<p>Tinted</p>",
    ],
  ])("pasting %s keeps the text and drops the markup", (_label, html, marker, expected) => {
    const full = makeEditor({});
    paste(full, html);
    expect(full.getHTML()).toContain(marker);

    const email = makeEditor(EMAIL);
    paste(email, html);
    expect(email.getHTML()).toBe(expected);
  });

  it("a dropped or pasted image file is neither uploaded nor inserted", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ location: "https://example.com/up.png" }),
    }));
    vi.stubGlobal("fetch", fetchMock);
    // ProseMirror's own drop handler asks where the drop landed; jsdom has no
    // layout, so answer "nowhere" and let it bow out.
    Object.defineProperty(document, "elementFromPoint", { value: () => null, configurable: true });
    const file = new File(["x"], "x.png", { type: "image/png" });
    const drop = (editor: Editor): Event => {
      const event = new Event("drop", { bubbles: true, cancelable: true });
      Object.defineProperty(event, "dataTransfer", { value: { files: [file] } });
      editor.view.dom.dispatchEvent(event);
      return event;
    };
    const pasteFile = (editor: Editor): Event => {
      const event = new Event("paste", { bubbles: true, cancelable: true });
      // getData answers ProseMirror's own paste handler, which reads the text.
      Object.defineProperty(event, "clipboardData", { value: { files: [file], getData: () => "" } });
      editor.view.dom.dispatchEvent(event);
      return event;
    };
    // Wait for the upload's promise chain (fetch, json, insert) to settle.
    const settle = async (): Promise<void> => {
      for (let i = 0; i < 10; i++) {
        await Promise.resolve();
      }
    };

    const full = makeEditor({ imageUploadUrl: "/upload/" }, "<p>a</p>");
    wireImageDropPaste(full);
    drop(full);
    await settle();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(full.getHTML()).toContain("<img");

    fetchMock.mockClear();
    const email = makeEditor({ ...EMAIL, imageUploadUrl: "/upload/" }, "<p>a</p>");
    wireImageDropPaste(email);
    // Not claimed either: the event is left for ProseMirror and the browser.
    expect(drop(email).defaultPrevented).toBe(false);
    expect(pasteFile(email).defaultPrevented).toBe(false);
    await settle();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(email.getHTML()).toBe("<p>a</p>");
  });

  it("inserting an image by URL is inert rather than a TypeError", () => {
    const email = makeEditor(EMAIL, "<p>a</p>");
    expect(() => insertImage(email, "https://example.com/x.png")).not.toThrow();
    expect(email.getHTML()).toBe("<p>a</p>");
  });

  it("an upload for a field without images never reaches the server", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const email = makeEditor({ ...EMAIL, imageUploadUrl: "/upload/" }, "<p>a</p>");
    await uploadAndInsert(email, new File(["x"], "x.png", { type: "image/png" }));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(email.getHTML()).toBe("<p>a</p>");
  });

  it("source view parses what is typed into it through the restricted schema", () => {
    const editor = makeEditor({ features: ["bold", "sourceView"] }, "<p>a</p>");
    toggleSourceView(editor);
    const source = document.querySelector<HTMLTextAreaElement>(".django-tiptap__source");
    expect(source).not.toBeNull();
    source!.value = "<h2>Title</h2><p><strong>b</strong></p>";
    toggleSourceView(editor);
    expect(editor.getHTML()).toBe("<p>Title</p><p><strong>b</strong></p>");
  });

  it("text-align and block styles name no heading when headings are off", () => {
    const editor = makeEditor({ features: ["textAlign"] }, "<p>a</p>");
    const options = (name: string): Record<string, unknown> =>
      editor.extensionManager.extensions.find((ext) => ext.name === name)!.options;
    expect(options("textAlign").types).toEqual(["paragraph"]);
    expect(options("blockStyle").types).toEqual(["paragraph"]);
    editor.commands.focus("end");
    expect(() => editor.commands.setTextAlign("center")).not.toThrow();
    expect(editor.getHTML()).toBe('<p style="text-align: center;">a</p>');
  });

  it("Enter still honours enterKey with lists excluded", () => {
    const editor = makeEditor({ features: ["bold"], enterKey: "hardBreak" }, "<p>ab</p>");
    editor.commands.focus("end");
    editor.view.dom.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }),
    );
    expect(editor.getHTML()).toBe("<p>ab<br></p>");
  });
});

describe("content saved before the field was restricted", () => {
  // A JSON-stored value written while the field still had headings and colours.
  // Restricting the field must not lose it: the excluded markup goes, the text
  // stays, exactly as for HTML.
  const ENVELOPE = {
    doc: {
      type: "doc",
      content: [
        { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "Title" }] },
        {
          type: "paragraph",
          content: [
            { type: "text", text: "b", marks: [{ type: "bold" }] },
            { type: "text", text: "red", marks: [{ type: "textStyle", attrs: { color: "red" } }] },
          ],
        },
      ],
    },
    html: '<h2>Title</h2><p><strong>b</strong><span style="color: red;">red</span></p>',
  };

  it("loads a JSON-stored document whose nodes the field no longer mounts", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const { default: DjangoTipTap } = await import("../src/index");
    const textarea = document.createElement("textarea");
    textarea.id = "restricted-json";
    textarea.setAttribute("data-tiptap-storage", "json");
    textarea.value = JSON.stringify(ENVELOPE);
    document.body.appendChild(textarea);
    const editor = DjangoTipTap.init(textarea, { features: ["bold"] });
    expect(editor.getHTML()).toBe("<p>Title</p><p><strong>b</strong>red</p>");
    DjangoTipTap.destroy("restricted-json");
  });

  it("loads the same document unchanged on an unrestricted field", async () => {
    const { default: DjangoTipTap } = await import("../src/index");
    const textarea = document.createElement("textarea");
    textarea.id = "full-json";
    textarea.setAttribute("data-tiptap-storage", "json");
    textarea.value = JSON.stringify(ENVELOPE);
    document.body.appendChild(textarea);
    const editor = DjangoTipTap.init(textarea, {});
    expect(editor.getHTML()).toBe(ENVELOPE.html);
    DjangoTipTap.destroy("full-json");
  });
});

describe("the toolbar of a restricted field", () => {
  it("renders none of the excluded buttons by default, and no empty group", () => {
    registerBuiltInButtons();
    const editor = makeEditor(EMAIL, "<p>a</p>");
    const toolbar = renderToolbar(editor, EMAIL);
    expect(toolbarKeys(toolbar.el)).toEqual([
      "undo",
      "redo",
      "bold",
      "italic",
      "paragraph",
      "bulletList",
      "orderedList",
      "link",
      "unlink",
      "clearFormatting",
    ]);
    for (const group of Array.from(toolbar.el.children)) {
      expect(group.childElementCount).toBeGreaterThan(0);
    }
    // Every button that did render has a command behind it.
    for (const button of Array.from(toolbar.el.querySelectorAll<HTMLButtonElement>("button[data-key]"))) {
      vi.spyOn(window, "prompt").mockReturnValue(null);
      expect(() => button.click()).not.toThrow();
    }
  });

  it("hides an explicitly listed but unavailable button and warns once, naming the feature", () => {
    registerBuiltInButtons();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const config: TipTapConfig = { ...EMAIL, toolbar: [["bold", "h2"], ["table"], ["italic"]] };
    const editor = makeEditor(config, "<p>a</p>");
    const toolbar = renderToolbar(editor, config);
    toolbar.refresh();
    toolbar.refresh();
    expect(toolbarKeys(toolbar.el)).toEqual(["bold", "italic"]);
    // The table group lost its only button, so it is not rendered at all.
    expect(toolbar.el.childElementCount).toBe(2);
    expect(warn).toHaveBeenCalledTimes(2);
    expect(warn.mock.calls[0][0]).toContain('"h2"');
    expect(warn.mock.calls[0][0]).toContain('"heading"');
    expect(warn.mock.calls[1][0]).toContain('"table"');
  });

  it("gives a custom region no built-in control the field cannot run", () => {
    registerBuiltInButtons();
    const restricted = rendererContext(makeEditor(EMAIL), EMAIL, (k: string) => k);
    expect(restricted.getButton("h2")).toBeUndefined();
    expect(restricted.getButton("sourceView")).toBeUndefined();
    expect(restricted.getButton("bold")).toBeDefined();
    expect(restricted.getButton("undo")).toBeDefined();
    const full = rendererContext(makeEditor({}), {}, (k: string) => k);
    expect(full.getButton("h2")).toBeDefined();
  });

  it("drops a merge tag's markup for an excluded feature and keeps its text", () => {
    registerBuiltInButtons();
    const config: TipTapConfig = {
      ...EMAIL,
      toolbar: [["mergeTags"]],
      mergeTags: [{ label: "Greeting", value: "<h2>Hello <strong>there</strong></h2>" }],
    };
    const editor = makeEditor(config, "<p></p>");
    const toolbar = renderToolbar(editor, config);
    document.body.appendChild(toolbar.el);
    editor.commands.focus("end");
    toolbar.el.querySelector<HTMLButtonElement>('[data-key="mergeTags"] button')!.click();
    toolbar.el.querySelector<HTMLButtonElement>(".django-tiptap__menu-item")!.click();
    expect(editor.getHTML()).toBe("<p>Hello <strong>there</strong></p>");
  });

  it("leaves consumer-registered buttons alone", () => {
    registerBuiltInButtons();
    registerButton("custom", { icon: "C", title: "custom", onClick: () => {} });
    const config: TipTapConfig = { features: [], toolbar: [["custom"]] };
    const editor = makeEditor(config, "<p>a</p>");
    expect(toolbarKeys(renderToolbar(editor, config).el)).toEqual(["custom"]);
    expect(getButton("custom")).toBeDefined();
  });
});

describe("minimal feature sets", () => {
  it("features: [] mounts the core alone and round-trips plain paragraphs", () => {
    const editor = makeEditor({ features: [] }, "<p>Hello <strong>bold</strong> world</p><p>Two</p>");
    const { nodes, marks, extensions } = names(editor);
    expect(nodes).toEqual(["doc", "hardBreak", "paragraph", "text"]);
    expect(marks).toEqual([]);
    for (const absent of [
      "textAlign",
      "characterCount",
      "fontSize",
      "color",
      "backgroundColor",
      "fontFamily",
      "imageResize",
      "listKeymap",
      "textStyle",
    ]) {
      expect(extensions).not.toContain(absent);
    }
    expect(extensions).toEqual(expect.arrayContaining(["undoRedo", "dropCursor", "gapCursor", "enterKey"]));
    expect(editor.getHTML()).toBe("<p>Hello bold world</p><p>Two</p>");
  });

  it("features: ['bold'] mounts exactly bold beyond the core", () => {
    const editor = makeEditor({ features: ["bold"] }, "<p>Hello <strong>bold</strong> <em>it</em></p>");
    const { nodes, marks } = names(editor);
    expect(nodes).toEqual(["doc", "hardBreak", "paragraph", "text"]);
    expect(marks).toEqual(["bold"]);
    expect(editor.getHTML()).toBe("<p>Hello <strong>bold</strong> it</p>");
  });
});

// The unrestricted editor as it was before `features` existed, captured from the
// tree that predates it. Order matters, not just membership: extension order is
// what decides how marks nest in getHTML(), so an unrestricted editor that merely
// held the same names could still change stored values.
const UNRESTRICTED_EXTENSIONS = [
  "paragraph",
  "enterKey",
  "link",
  "listItemBranchingDeleteKeymap",
  "textStyle",
  "editable",
  "clipboardTextSerializer",
  "commands",
  "focusEvents",
  "keymap",
  "tabindex",
  "drop",
  "paste",
  "delete",
  "textDirection",
  "starterKit",
  "bold",
  "blockquote",
  "bulletList",
  "code",
  "codeBlock",
  "doc",
  "dropCursor",
  "gapCursor",
  "hardBreak",
  "heading",
  "undoRedo",
  "horizontalRule",
  "italic",
  "listItem",
  "listKeymap",
  "orderedList",
  "strike",
  "text",
  "blockStyle",
  "underline",
  "fontFamily",
  "color",
  "backgroundColor",
  "fontSize",
  "textAlign",
  "image",
  "table",
  "tableRow",
  "tableHeader",
  "tableCell",
  "subscript",
  "superscript",
  "characterCount",
  "imageResize",
];
const UNRESTRICTED_NODES = [
  "blockquote",
  "bulletList",
  "codeBlock",
  "doc",
  "hardBreak",
  "heading",
  "horizontalRule",
  "image",
  "listItem",
  "orderedList",
  "paragraph",
  "table",
  "tableCell",
  "tableHeader",
  "tableRow",
  "text",
];
const UNRESTRICTED_MARKS = [
  "bold",
  "code",
  "italic",
  "link",
  "strike",
  "subscript",
  "superscript",
  "textStyle",
  "underline",
];
const UNRESTRICTED_TOOLBAR = [
  "undo",
  "redo",
  "bold",
  "italic",
  "underline",
  "strike",
  "code",
  "fontSize",
  "fontFamily",
  "color",
  "highlight",
  "h1",
  "h2",
  "h3",
  "paragraph",
  "bulletList",
  "orderedList",
  "blockquote",
  "alignLeft",
  "alignCenter",
  "alignRight",
  "alignJustify",
  "image",
  "table",
  "link",
  "unlink",
  "clearFormatting",
  "sourceView",
];

// Every name the server's feature model knows: the core plus every feature.
const ALL_FEATURES = [
  "backgroundColor",
  "blockquote",
  "bold",
  "bulletList",
  "characterCount",
  "code",
  "codeBlock",
  "color",
  "fontFamily",
  "fontSize",
  "heading",
  "highlight",
  "horizontalRule",
  "image",
  "italic",
  "link",
  "listItem",
  "orderedList",
  "sourceView",
  "strike",
  "subscript",
  "superscript",
  "table",
  "tableCell",
  "tableHeader",
  "tableRow",
  "textAlign",
  "textStyle",
  "underline",
];

describe("an unrestricted field is unchanged", () => {
  it.each([
    ["no features key", {}],
    ["features: undefined", { features: undefined }],
    ["features: null", { features: null }],
    ["every feature listed", { features: ALL_FEATURES }],
  ])("%s mounts the same extensions, schema and toolbar as before", (_label, config) => {
    registerBuiltInButtons();
    const editor = makeEditor(config as TipTapConfig, "<p>a</p>");
    const { nodes, marks, extensions } = names(editor);
    expect(extensions).toEqual(UNRESTRICTED_EXTENSIONS);
    expect(nodes).toEqual(UNRESTRICTED_NODES);
    expect(marks).toEqual(UNRESTRICTED_MARKS);
    const toolbar = renderToolbar(editor, config as TipTapConfig);
    expect(toolbarKeys(toolbar.el)).toEqual(UNRESTRICTED_TOOLBAR);
    expect(toolbar.el.childElementCount).toBe(9);
  });
});
