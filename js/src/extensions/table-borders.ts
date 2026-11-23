// Ruled tables. The table node's `border` (a literal cell border shorthand such
// as "1px solid #d0d5dd"; null when unruled) is the source of truth: it renders
// border="1" and border-collapse on <table>, and is copied onto every cell's own
// `border`, which renders as an inline style, because email clients read
// neither stylesheets nor CSS variables. Unruled tables render exactly as the
// stock nodes do, and their cells keep any hand-written border of their own.
import { Table, TableCell, TableHeader } from "../tiptap-runtime";
import type { Editor } from "../tiptap-runtime";

type EditorState = Editor["state"];
type Transaction = EditorState["tr"];
type PMNode = EditorState["doc"];
type PMPlugin = EditorState["plugins"][number];

export const DEFAULT_TABLE_BORDER = "1px solid #d0d5dd";

const SOLID_BORDER_RE = /^(\S+)\s+solid\s+(.+)$/;

// The width and colour of a `<width> solid <colour>` border, else the default
// lines' own, so a hand-written `2px dotted red` reads as 1px and #d0d5dd.
export function tableBorderParts(value: unknown): { width: string; color: string } {
  const match = typeof value === "string" ? SOLID_BORDER_RE.exec(value) : null;
  return match ? { width: match[1], color: match[2] } : { width: "1px", color: "#d0d5dd" };
}

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    tableBorders: {
      /** Rule the table at the selection, giving every cell `value` as its border. */
      setTableBorder: (value: string) => ReturnType;
      /** Remove the rules from the table at the selection and from each of its cells. */
      unsetTableBorder: () => ReturnType;
    };
  }
}

// The last `border` declaration of an inline style, as written: read from the
// attribute text rather than el.style, which would turn #d0d5dd into rgb().
function inlineBorder(el: Element): string | null {
  let found: string | null = null;
  for (const declaration of (el.getAttribute("style") ?? "").split(";")) {
    const at = declaration.indexOf(":");
    if (at > 0 && declaration.slice(0, at).trim().toLowerCase() === "border") {
      found = declaration.slice(at + 1).trim() || null;
    }
  }
  return found;
}

// A <table border="N"> with a whole N above 0 is ruled, with its first cell's
// own border, or the default lines when that cell has none.
function tableBorder(table: Element): string | null {
  const width = table.getAttribute("border") ?? "";
  if (!/^[0-9]+$/.test(width) || Number(width) === 0) {
    return null;
  }
  const first = table.querySelector("th, td");
  return (first && inlineBorder(first)) || DEFAULT_TABLE_BORDER;
}

// A cell of a ruled table takes the table's border, so content loaded without a
// transaction is as consistent as content the sync below has seen.
const cellBorder = {
  border: {
    default: null,
    parseHTML: (el: HTMLElement) => {
      const table = el.closest("table");
      return (table && tableBorder(table)) ?? inlineBorder(el);
    },
    renderHTML: (attrs: Record<string, unknown>) =>
      attrs.border ? { style: `border: ${attrs.border as string}` } : {},
  },
};

export const RuledTableCell = TableCell.extend({
  addAttributes() {
    return { ...this.parent?.(), ...cellBorder };
  },
});

export const RuledTableHeader = TableHeader.extend({
  addAttributes() {
    return { ...this.parent?.(), ...cellBorder };
  },
});

// Each cell of `table` (at `pos`) whose border is not `value`, with its position.
function cellsToSet(table: PMNode, pos: number, value: unknown): [number, PMNode][] {
  const found: [number, PMNode][] = [];
  table.forEach((row, rowOffset) => {
    row.forEach((cell, cellOffset) => {
      if (cell.attrs.border !== value) {
        found.push([pos + 1 + rowOffset + 1 + cellOffset, cell]);
      }
    });
  });
  return found;
}

function setCells(tr: Transaction, table: PMNode, pos: number, value: unknown): void {
  for (const [at, cell] of cellsToSet(table, pos, value)) {
    tr.setNodeMarkup(at, undefined, { ...cell.attrs, border: value });
  }
}

// The innermost table around the selection, and its position.
function tableAt(state: EditorState): { node: PMNode; pos: number } | null {
  const { $from } = state.selection;
  for (let depth = $from.depth; depth > 0; depth -= 1) {
    const node = $from.node(depth);
    if (node.type.name === "table") {
      return { node, pos: $from.before(depth) };
    }
  }
  return null;
}

function setBorder(value: string | null) {
  return ({ state, tr, dispatch }: { state: EditorState; tr: Transaction; dispatch?: unknown }): boolean => {
    const table = tableAt(state);
    if (!table) {
      return false;
    }
    if (dispatch) {
      tr.setNodeMarkup(table.pos, undefined, { ...table.node.attrs, border: value });
      setCells(tr, table.node, table.pos, value);
    }
    return true;
  };
}

export const RuledTable = Table.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      border: {
        default: null,
        parseHTML: (el: HTMLElement) => tableBorder(el),
        renderHTML: (attrs: Record<string, unknown>) => (attrs.border ? { border: "1" } : {}),
      },
    };
  },

  renderHTML(props) {
    const spec = this.parent?.(props) as [string, Record<string, string>, ...unknown[]];
    if (!props.node.attrs.border) {
      return spec;
    }
    const [tag, attrs, ...rest] = spec;
    const style = attrs.style ? `${attrs.style}; border-collapse: collapse` : "border-collapse: collapse";
    return [tag, { ...attrs, style }, ...rest];
  },

  addCommands() {
    return {
      ...this.parent?.(),
      setTableBorder: (value: string) => setBorder(value),
      unsetTableBorder: () => setBorder(null),
    };
  },

  // Rows and columns prosemirror-tables adds, and the cells its fixTables fills
  // a ragged table out with, are fresh cells with no border. The Plugin class
  // is the table's own, so the glue imports nothing from @tiptap/pm.
  addProseMirrorPlugins() {
    const plugins = this.parent?.() ?? [];
    const PluginClass = plugins[0].constructor as new (spec: PMPlugin["spec"]) => PMPlugin;
    const sync = new PluginClass({
      appendTransaction(transactions, _old, state) {
        if (!transactions.some((tr) => tr.docChanged)) {
          return null;
        }
        const tr = state.tr;
        state.doc.descendants((node, pos) => {
          if (node.type.name === "table" && node.attrs.border) {
            setCells(tr, node, pos, node.attrs.border);
          }
          return true;
        });
        return tr.docChanged ? tr : null;
      },
    });
    return [...plugins, sync];
  },
});
