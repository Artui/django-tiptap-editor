// Content-fidelity comparator used by the corpus round-trip test. Normalizes
// away differences that are not content loss: attribute + style-declaration
// order, color notation (hex <-> rgb), CSS box shorthand, pretty-print
// whitespace between blocks, <mark> vs <span> highlight, and the <p> wrapper
// TipTap inserts inside <li>. Whatever survives is genuine drift.

const BLOCK = new Set([
  "p", "div", "ul", "ol", "li", "table", "thead", "tbody", "tfoot", "tr", "td", "th",
  "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "hr", "figure", "figcaption",
  "section", "article", "header", "footer", "pre", "caption", "colgroup", "col",
]);
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "col"]);

function normColor(s: string): string {
  s = s.replace(/rgba?\(([^)]+)\)/gi, (m, inner: string) => {
    const p = inner.split(",").map((x) => x.trim());
    if (p.length >= 3) {
      const to = (n: string) => ("0" + parseInt(n, 10).toString(16)).slice(-2);
      return "#" + to(p[0]) + to(p[1]) + to(p[2]);
    }
    return m;
  });
  s = s.replace(/#([0-9a-fA-F]{3,6})\b/g, (_m, h: string) => {
    h = h.toLowerCase();
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    return "#" + h;
  });
  return s;
}

function expandBox(val: string): string {
  let t = val.trim().split(/\s+/).map((x) => (x === "0" ? "0px" : x));
  if (t.length === 1) t = [t[0], t[0], t[0], t[0]];
  else if (t.length === 2) t = [t[0], t[1], t[0], t[1]];
  else if (t.length === 3) t = [t[0], t[1], t[2], t[1]];
  return t.join(" ");
}

function normDecl(decl: string): string {
  let d = decl.replace(/\s*:\s*/, ": ");
  const m = d.match(/^(margin|padding)\s*:\s*(.+)$/);
  if (m) d = m[1] + ": " + expandBox(m[2]);
  return d;
}

function isBlock(n: Node | null): boolean {
  return !!n && n.nodeType === 1 && BLOCK.has((n as Element).tagName.toLowerCase());
}

function ser(node: Node): string {
  if (node.nodeType === 3) {
    const prev = node.previousSibling;
    const next = node.nextSibling;
    const t = node.textContent ?? "";
    if (/^\s*$/.test(t)) {
      const po = !prev || isBlock(prev);
      const no = !next || isBlock(next);
      return po && no ? "" : " ";
    }
    let s = t.replace(/\s+/g, " ");
    if (!prev || isBlock(prev)) s = s.replace(/^ /, "");
    if (!next || isBlock(next)) s = s.replace(/ $/, "");
    return s;
  }
  if (node.nodeType !== 1) return "";
  const el = node as Element;
  let tag = el.tagName.toLowerCase();
  if (tag === "mark") tag = "span";
  const attrs = Array.from(el.attributes)
    .map((a) => {
      let v = a.value;
      if (a.name === "style") {
        v = normColor(v)
          .split(";")
          .map((s) => s.trim())
          .filter(Boolean)
          .map(normDecl)
          .sort()
          .join("; ");
        if (v) v += ";";
      }
      return [a.name, v] as const;
    })
    .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  const attrStr = attrs.map((a) => ` ${a[0]}="${a[1]}"`).join("");
  if (VOID.has(tag)) return `<${tag}${attrStr}>`;
  // unwrap the <p> wrapper TipTap inserts inside <li>
  if (tag === "li") {
    let inner = "";
    el.childNodes.forEach((c) => {
      if (c.nodeType === 1 && (c as Element).tagName.toLowerCase() === "p") {
        (c as Element).childNodes.forEach((g) => (inner += ser(g)));
      } else {
        inner += ser(c);
      }
    });
    return `<li${attrStr}>${inner}</li>`;
  }
  let body = "";
  el.childNodes.forEach((c) => (body += ser(c)));
  return `<${tag}${attrStr}>${body}</${tag}>`;
}

export function canonicalLoose(html: string): string {
  const doc = new DOMParser().parseFromString(`<div id="r">${html}</div>`, "text/html");
  const root = doc.getElementById("r")!;
  let out = "";
  root.childNodes.forEach((c) => (out += ser(c)));
  return out.trim();
}

// All non-whitespace characters, in order — the strongest "no text loss"
// guarantee. Whitespace is stripped entirely because block separation differs
// between TinyMCE's pretty-printed output (newlines between blocks) and TipTap's
// compact output; this check still catches any dropped character or word.
export function textOf(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  return (doc.body.textContent ?? "").replace(/\s+/g, "");
}
