// A ruled table: the table node's `border` is the source of truth, rendered as
// border="1" and border-collapse on <table> and a literal border on every cell.
import { afterEach, describe, expect, it } from "vitest";

import { buildExtensions } from "../src/build-extensions";
import { getTranslator } from "../src/i18n";
import { Editor } from "../src/tiptap-runtime";

const LINES = "1px solid #d0d5dd";
const LINES_RGB = "1px solid rgb(208, 213, 221)";
const TWO_BY_TWO = "<table><tbody><tr><th><p>a</p></th><th><p>b</p></th></tr><tr><td><p>c</p></td><td><p>d</p></td></tr></tbody></table>";
const REPRO =
  '<table border="1" style="border-collapse: collapse; border: 1px solid #000; width: 100%"><tbody><tr>' +
  '<th style="border: 1px solid #000">A</th><td style="border: 1px solid #000; text-align: left">1</td>' +
  "</tr></tbody></table>";

let editor: Editor;

function make(content = ""): Editor {
  editor = new Editor({
    element: document.createElement("div"),
    content,
    extensions: buildExtensions({}, { tiptap: {}, locale: "en", t: (k) => k }),
  });
  return editor;
}

function inCell(e: Editor): Editor {
  let pos = 0;
  e.state.doc.descendants((node, at) => {
    if (pos === 0 && node.type.name === "paragraph") {
      pos = at + 1;
    }
  });
  e.commands.setTextSelection(pos);
  return e;
}

type Cmds = Record<string, (...args: unknown[]) => boolean>;
const run = (e: Editor, name: string, ...args: unknown[]): boolean =>
  (e.commands as unknown as Cmds)[name](...args);

function cells(html: string): HTMLElement[] {
  const root = document.createElement("template");
  root.innerHTML = html;
  return Array.from(root.content.querySelectorAll<HTMLElement>("th, td"));
}

function tableOf(html: string): HTMLElement {
  const root = document.createElement("template");
  root.innerHTML = html;
  return root.content.querySelector("table") as HTMLElement;
}

afterEach(() => {
  editor?.destroy();
});

describe("a ruled table", () => {
  it("renders border=1 and border-collapse on the table and a literal border on every cell", () => {
    const e = inCell(make(TWO_BY_TWO));
    expect(run(e, "setTableBorder", LINES)).toBe(true);
    expect(e.getHTML()).toBe(
      '<table border="1" style="min-width: 50px; border-collapse: collapse;"><colgroup>' +
        '<col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody>' +
        `<tr><th style="border: ${LINES_RGB};"><p>a</p></th><th style="border: ${LINES_RGB};"><p>b</p></th></tr>` +
        `<tr><td style="border: ${LINES_RGB};"><p>c</p></td><td style="border: ${LINES_RGB};"><p>d</p></td></tr>` +
        "</tbody></table>",
    );
    const json = e.getJSON().content?.[0];
    expect(json?.attrs?.border).toBe(LINES);
    expect(json?.content?.[1].content?.[0].attrs?.border).toBe(LINES);
  });

  it("keeps a sized table's width beside border-collapse", () => {
    const e = inCell(
      make('<table><tbody><tr><td colwidth="120"><p>a</p></td><td colwidth="80"><p>b</p></td></tr></tbody></table>'),
    );
    run(e, "setTableBorder", LINES);
    expect(tableOf(e.getHTML()).getAttribute("style")).toBe("width: 200px; border-collapse: collapse;");
  });

  it("keeps a table's min-width beside border-collapse", () => {
    const e = inCell(make(TWO_BY_TWO));
    run(e, "setTableBorder", LINES);
    expect(tableOf(e.getHTML()).getAttribute("style")).toBe("min-width: 50px; border-collapse: collapse;");
  });

  it.each(["addRowBefore", "addRowAfter", "addColumnBefore", "addColumnAfter"])(
    "%s gives the new cells the table's border",
    (command) => {
      const e = inCell(make(TWO_BY_TWO));
      run(e, "setTableBorder", LINES);
      run(e, command);
      const found = cells(e.getHTML());
      expect(found.length).toBeGreaterThan(4);
      expect(found.map((cell) => cell.getAttribute("style"))).toEqual(found.map(() => `border: ${LINES_RGB};`));
    },
  );

  it("rules the cells added beside a cell spanning two rows", () => {
    const e = inCell(
      make('<table><tbody><tr><td rowspan="2"><p>a</p></td><td><p>b</p></td></tr><tr><td><p>c</p></td></tr></tbody></table>'),
    );
    run(e, "setTableBorder", LINES);
    run(e, "addColumnAfter");
    run(e, "addRowAfter");
    const found = cells(e.getHTML());
    expect(found.length).toBeGreaterThan(3);
    expect(found.every((cell) => cell.style.border === LINES_RGB)).toBe(true);
  });

  it("unsetTableBorder clears the table and every cell", () => {
    const e = inCell(make(TWO_BY_TWO));
    const unruled = e.getHTML();
    run(e, "setTableBorder", LINES);
    expect(run(e, "unsetTableBorder")).toBe(true);
    expect(e.getHTML()).toBe(unruled);
  });

  it("is one undo step", () => {
    const e = inCell(make(TWO_BY_TWO));
    const unruled = e.getHTML();
    run(e, "setTableBorder", LINES);
    e.commands.undo();
    expect(e.getHTML()).toBe(unruled);
  });

  it("does nothing outside a table", () => {
    const e = make("<p>x</p>");
    e.commands.setTextSelection(1);
    expect(run(e, "setTableBorder", LINES)).toBe(false);
    expect(run(e, "unsetTableBorder")).toBe(false);
  });
});

describe("parsing ruled markup", () => {
  it("keeps the card's hand-written table ruled, its cells' borders and alignment", () => {
    const e = make(REPRO);
    const html = e.getHTML();
    const table = tableOf(html);
    expect(table.getAttribute("border")).toBe("1");
    expect(table.style.borderCollapse).toBe("collapse");
    expect(cells(html).map((cell) => cell.getAttribute("style"))).toEqual([
      "border: 1px solid rgb(0, 0, 0);",
      "text-align: left; border: 1px solid rgb(0, 0, 0);",
    ]);
    expect(e.getJSON().content?.[0].attrs?.border).toBe("1px solid #000");
  });

  it("rules bare cells of a <table border> with the default lines on load", () => {
    const html = make('<table border="1"><tbody><tr><td><p>a</p></td><td><p>b</p></td></tr></tbody></table>').getHTML();
    expect(tableOf(html).getAttribute("border")).toBe("1");
    expect(cells(html).map((cell) => cell.style.border)).toEqual([LINES_RGB, LINES_RGB]);
  });

  it("writes a legacy border=2 back as border=1", () => {
    const html = make('<table border="2"><tbody><tr><td><p>a</p></td></tr></tbody></table>').getHTML();
    expect(tableOf(html).getAttribute("border")).toBe("1");
  });

  it.each(['border="0"', 'border="x"', 'border=""', "border"])("reads a table with %s as unruled", (attr) => {
    const html = make(`<table ${attr}><tbody><tr><td><p>a</p></td></tr></tbody></table>`).getHTML();
    expect(tableOf(html).hasAttribute("border")).toBe(false);
    expect(cells(html)[0].hasAttribute("style")).toBe(false);
  });

  it("keeps a hand-written cell border on an unruled table, through an edit", () => {
    const e = inCell(
      make('<table><tbody><tr><td style="border: 2px dotted #f00"><p>a</p></td><td><p>b</p></td></tr></tbody></table>'),
    );
    e.commands.insertContent("z");
    const html = e.getHTML();
    expect(tableOf(html).hasAttribute("border")).toBe(false);
    expect(cells(html).map((cell) => cell.style.border)).toEqual(["2px dotted rgb(255, 0, 0)", ""]);
  });

  it("leaves an unruled table's markup as it was", () => {
    expect(make(TWO_BY_TWO).getHTML()).toBe(
      '<table style="min-width: 50px;"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup>' +
        "<tbody><tr><th><p>a</p></th><th><p>b</p></th></tr><tr><td><p>c</p></td><td><p>d</p></td></tr></tbody></table>",
    );
  });
});

describe("the table-menu item", () => {
  it.each([
    ["en", "Add table lines", "Remove table lines"],
    ["sv", "Lägg till tabellinjer", "Ta bort tabellinjer"],
  ])("is labelled in %s", (locale, on, off) => {
    const t = getTranslator(locale);
    expect([t("tableLinesOn"), t("tableLinesOff")]).toEqual([on, off]);
  });
});
