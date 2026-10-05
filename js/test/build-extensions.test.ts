// StarterKit 3 bundles its own Link and Underline, and the baseline registers
// configured ones of each beside it. Two registrations of one name are a tiptap
// warning and an undefined winner -- StarterKit's Link would bring back the
// autolink and open-on-click the configured one turns off -- and nothing else
// in the suite notices: every rendering test passes with either copy winning.
import { afterEach, expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import { Editor } from "../src/tiptap-runtime";

const ctx = { tiptap: {}, locale: "en", t: (k: string) => k };

afterEach(() => {
  document.body.innerHTML = "";
});

it("registers every extension name once", () => {
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({ element, extensions: buildExtensions({}, ctx) });
  const names = editor.extensionManager.extensions.map((extension) => extension.name);
  const repeated = names.filter((name, index) => names.indexOf(name) !== index);
  // The two the baseline replaces are there at all, so an empty list is not
  // an editor that registered neither.
  expect(names).toEqual(expect.arrayContaining(["link", "underline"]));
  expect(repeated).toEqual([]);
  editor.destroy();
});
