// Source view against the form it is bound to: whatever the field carries when
// the form is submitted must be what the schema produces from the visible
// source, in the field's storage format. Before the submit flush, HTML mode
// copied raw mid-edit markup into the field on every keystroke and JSON mode
// copied nothing at all, so a submit with source view open either saved
// un-normalised HTML or dropped the edit.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DjangoTipTap from "../src/index";
import { toggleSourceView } from "../src/toolbar/source-view";

const DOC = {
  type: "doc",
  content: [{ type: "paragraph", content: [{ type: "text", text: "hello" }] }],
};

// Markup the schema does not model: the <script> is dropped and the stray <em>
// is normalised on re-parse, so its survival in the field proves no flush ran.
const RAW = "<p>edited</p><script>alert(1)</script><em>x";

function mount(id: string, attrs: Record<string, string>, value: string) {
  const form = document.createElement("form");
  const textarea = document.createElement("textarea");
  textarea.id = id;
  textarea.name = "body";
  for (const [key, val] of Object.entries(attrs)) {
    textarea.setAttribute(key, val);
  }
  textarea.value = value;
  form.appendChild(textarea);
  document.body.appendChild(form);
  return { form, textarea, editor: DjangoTipTap.init(textarea, {}) };
}

function sourceTextarea(): HTMLTextAreaElement {
  const el = document.querySelector<HTMLTextAreaElement>("textarea.django-tiptap__source");
  if (!el) {
    throw new Error("source view is not open");
  }
  return el;
}

function typeSource(html: string): void {
  const source = sourceTextarea();
  source.value = html;
  source.dispatchEvent(new Event("input", { bubbles: true }));
}

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("submitting with source view open", () => {
  it("HTML mode: flushes the source through the schema, not raw markup", () => {
    const { form, textarea, editor } = mount("sv-html", {}, "<p>hello</p>");
    toggleSourceView(editor);
    typeSource(RAW);
    // Un-normalised markup must not reach the field just because it was typed.
    expect(textarea.value).not.toContain("script");
    expect(textarea.value).toContain("hello");

    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    expect(textarea.value).toContain("edited");
    expect(textarea.value).not.toContain("script");
    expect(textarea.value).toBe(editor.getHTML());
    DjangoTipTap.destroy("sv-html");
  });

  it("JSON mode: flushes the source into the envelope instead of losing it", () => {
    const { form, textarea, editor } = mount(
      "sv-json",
      { "data-tiptap-storage": "json" },
      JSON.stringify({ doc: DOC, html: "<p>hello</p>" }),
    );
    toggleSourceView(editor);
    typeSource(RAW);

    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    const envelope = JSON.parse(textarea.value);
    expect(envelope.html).toContain("edited");
    expect(envelope.html).not.toContain("script");
    expect(JSON.stringify(envelope.doc)).toContain("edited");
    expect(envelope.html).toBe(editor.getHTML());
    DjangoTipTap.destroy("sv-json");
  });

  it("closes source view so the normalised content is what the author sees", () => {
    const { form, editor } = mount("sv-close", {}, "<p>hello</p>");
    toggleSourceView(editor);
    typeSource(RAW);
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(document.querySelector(".django-tiptap__source")).toBeNull();
    expect(editor.isEditable).toBe(true);
    DjangoTipTap.destroy("sv-close");
  });

  it("flushes on formdata too, for ajax submits that never fire submit", () => {
    // jsdom has no FormDataEvent; browsers fire this when a FormData is built
    // from the form, which is how htmx and friends serialise it.
    const { form, textarea, editor } = mount("sv-fd", {}, "<p>hello</p>");
    toggleSourceView(editor);
    typeSource(RAW);
    form.dispatchEvent(new Event("formdata", { bubbles: true }));
    expect(textarea.value).toContain("edited");
    DjangoTipTap.destroy("sv-fd");
  });

  it("ignores another form's submit", () => {
    const { editor } = mount("sv-other", {}, "<p>hello</p>");
    const other = document.createElement("form");
    document.body.appendChild(other);
    toggleSourceView(editor);
    typeSource(RAW);
    other.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(sourceTextarea().value).toBe(RAW);
    DjangoTipTap.destroy("sv-other");
  });

  it("stops listening once the editor is destroyed", () => {
    const { form, textarea, editor } = mount("sv-gone", {}, "<p>hello</p>");
    toggleSourceView(editor);
    DjangoTipTap.destroy("sv-gone");
    const value = textarea.value;
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(textarea.value).toBe(value);
  });
});
