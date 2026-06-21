// JSON storage mode: the textarea carries a {doc, html} envelope. Asserts the
// editor hydrates from the envelope's doc and writes a fresh envelope back on
// edit (the TipTapJSONField contract), while HTML mode stays plain getHTML().
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";

const DOC = {
  type: "doc",
  content: [{ type: "paragraph", content: [{ type: "text", text: "hello" }] }],
};

function makeTextarea(id: string, attrs: Record<string, string>, value: string) {
  const ta = document.createElement("textarea");
  ta.id = id;
  for (const [k, v] of Object.entries(attrs)) {
    ta.setAttribute(k, v);
  }
  ta.value = value;
  document.body.appendChild(ta);
  return ta;
}

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("JSON storage mode", () => {
  it("hydrates from the envelope doc and writes an envelope on edit", () => {
    const ta = makeTextarea(
      "ed-json",
      { "data-tiptap-storage": "json" },
      JSON.stringify({ doc: DOC, html: "<p>hello</p>" }),
    );
    const editor = DjangoTipTap.init(ta, {});

    expect(editor.getText()).toBe("hello");

    editor.commands.focus("end");
    editor.commands.insertContent(" world");
    const env = JSON.parse(ta.value);
    expect(env.doc.type).toBe("doc");
    expect(env.html).toContain("hello world");

    DjangoTipTap.destroy("ed-json");
  });

  it("starts blank on an empty JSON field", () => {
    const ta = makeTextarea("ed-empty", { "data-tiptap-storage": "json" }, "");
    const editor = DjangoTipTap.init(ta, {});
    expect(editor.getText()).toBe("");
    DjangoTipTap.destroy("ed-empty");
  });

  it("falls back to the html mirror when the doc is empty (lazy migration)", () => {
    // A record seeded with only legacy HTML in the mirror (no doc yet).
    const ta = makeTextarea(
      "ed-seed",
      { "data-tiptap-storage": "json" },
      JSON.stringify({ doc: {}, html: "<p>legacy content</p>" }),
    );
    const editor = DjangoTipTap.init(ta, {});
    expect(editor.getText()).toBe("legacy content");
    // First edit persists a real {doc, html} envelope.
    editor.commands.focus("end");
    editor.commands.insertContent("!");
    const env = JSON.parse(ta.value);
    expect(env.doc.content.length).toBeGreaterThan(0);
    DjangoTipTap.destroy("ed-seed");
  });

  it("recovers from an invalid JSON value", () => {
    const ta = makeTextarea("ed-bad", { "data-tiptap-storage": "json" }, "{not json");
    const editor = DjangoTipTap.init(ta, {});
    expect(editor.getText()).toBe("");
    expect(console.error).toHaveBeenCalled();
    DjangoTipTap.destroy("ed-bad");
  });

  it("HTML mode writes plain getHTML(), not an envelope", () => {
    const ta = makeTextarea("ed-html", {}, "<p>hi</p>");
    const editor = DjangoTipTap.init(ta, {});
    editor.commands.insertContent("!");
    expect(ta.value.startsWith("<")).toBe(true);
    expect(ta.value).toContain("hi");
    DjangoTipTap.destroy("ed-html");
  });
});
