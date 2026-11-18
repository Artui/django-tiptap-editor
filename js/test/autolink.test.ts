// The `autolink` config key and the linkProtocols filter on autolinked and
// pasted plain URLs. Tiptap's own `protocols` adds to a built-in list (ftp,
// mailto, sms, ...) rather than restricting it, so the filter is ours.
import { afterEach, describe, expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import type { TipTapConfig } from "../src/default-config";
import { Editor } from "../src/tiptap-runtime";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };

function makeEditor(config: TipTapConfig): Editor {
  const element = document.createElement("div");
  document.body.appendChild(element);
  return new Editor({ element, content: "<p></p>", extensions: buildExtensions(config, ctx) });
}

function type(editor: Editor, text: string): void {
  editor.commands.focus("end");
  for (const ch of text) {
    editor.view.dispatch(editor.state.tr.insertText(ch));
  }
}

// jsdom has no ClipboardEvent; a plain paste event drives the same paste rules.
function paste(editor: Editor, text: string): void {
  editor.commands.focus("end");
  editor.view.pasteText(text, new Event("paste") as ClipboardEvent);
}

function hrefs(editor: Editor): string[] {
  return Array.from(editor.view.dom.querySelectorAll("a")).map((a) => a.getAttribute("href") ?? "");
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("autolink config", () => {
  it("is off by default: typing a URL makes no link", () => {
    const editor = makeEditor({});
    expect(editor.extensionManager.extensions.find((e) => e.name === "link")?.options.autolink).toBe(
      false,
    );
    type(editor, "see https://example.org ");
    expect(hrefs(editor)).toEqual([]);
    editor.destroy();
  });

  it("links a typed URL whose scheme is in linkProtocols", () => {
    const editor = makeEditor({ autolink: true, linkProtocols: ["http", "https"] });
    type(editor, "see https://example.org ");
    expect(hrefs(editor)).toEqual(["https://example.org"]);
    editor.destroy();
  });

  it("does not link a typed ftp URL or bare email outside linkProtocols", () => {
    const editor = makeEditor({ autolink: true, linkProtocols: ["http", "https"] });
    type(editor, "ftp://example.org and a@b.org or https://example.org ");
    expect(hrefs(editor)).toEqual(["https://example.org"]);
    editor.destroy();
  });

  it("links a typed bare email when mailto is allowed", () => {
    const editor = makeEditor({ autolink: true });
    type(editor, "write a@b.org ");
    expect(hrefs(editor)).toEqual(["mailto:a@b.org"]);
    editor.destroy();
  });

  it("mounts without a link extension when features exclude link", () => {
    const editor = makeEditor({ autolink: true, features: ["bold"] });
    expect(editor.extensionManager.extensions.some((e) => e.name === "link")).toBe(false);
    type(editor, "see https://example.org ");
    expect(hrefs(editor)).toEqual([]);
    editor.destroy();
  });
});

describe("pasted plain URLs", () => {
  it("are not linked outside linkProtocols, with autolink off", () => {
    const editor = makeEditor({ linkProtocols: ["http", "https"] });
    paste(editor, "ftp://example.org and a@b.org");
    expect(hrefs(editor)).toEqual([]);
    editor.destroy();
  });

  it("are linked inside linkProtocols, schemeless ones by the default protocol", () => {
    const editor = makeEditor({ linkProtocols: ["http", "https"] });
    paste(editor, "https://a.org and www.b.org");
    expect(hrefs(editor)).toEqual(["https://a.org", "http://www.b.org"]);
    editor.destroy();
  });
});
