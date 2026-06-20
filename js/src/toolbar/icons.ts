// Built-in toolbar icons. Each value is icon markup assigned to a button's
// innerHTML; consumers override any of them via ui.registerButton. Mark/heading
// glyphs are styled text (a familiar word-processor idiom and robust across
// fonts); structural controls are minimal stroke SVGs that inherit currentColor.
const svg = (body: string): string =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;

const glyph = (text: string, style = ""): string =>
  `<span class="django-tiptap__glyph" style="${style}">${text}</span>`;

export const ICONS: Record<string, string> = {
  undo: svg('<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-4"/>'),
  redo: svg('<path d="m15 14 5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h4"/>'),

  bold: glyph("B", "font-weight:700"),
  italic: glyph("I", "font-style:italic;font-family:serif"),
  underline: glyph("U", "text-decoration:underline"),
  strike: glyph("S", "text-decoration:line-through"),
  code: glyph("&lt;/&gt;", "font-family:ui-monospace,monospace;font-size:0.8em"),

  h1: glyph("H1", "font-weight:700;font-size:0.78em"),
  h2: glyph("H2", "font-weight:700;font-size:0.78em"),
  h3: glyph("H3", "font-weight:700;font-size:0.78em"),
  paragraph: glyph("¶", "font-size:1.05em"),

  bulletList: svg(
    '<circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/><line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="18" x2="20" y2="18"/>',
  ),
  orderedList: svg(
    '<line x1="10" y1="6" x2="20" y2="6"/><line x1="10" y1="12" x2="20" y2="12"/><line x1="10" y1="18" x2="20" y2="18"/><path d="M4 6V3l-1 1"/><path d="M3 12h2l-2 3h2" stroke-width="1.6"/>',
  ),
  blockquote: glyph("&#8220;", "font-size:1.5em;line-height:1"),

  alignLeft: svg('<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="14" y2="12"/><line x1="3" y1="18" x2="18" y2="18"/>'),
  alignCenter: svg('<line x1="3" y1="6" x2="21" y2="6"/><line x1="7" y1="12" x2="17" y2="12"/><line x1="5" y1="18" x2="19" y2="18"/>'),
  alignRight: svg('<line x1="3" y1="6" x2="21" y2="6"/><line x1="10" y1="12" x2="21" y2="12"/><line x1="6" y1="18" x2="21" y2="18"/>'),
  alignJustify: svg('<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>'),

  image: svg('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="m4 17 4.5-4.5a2 2 0 0 1 3 0L20 17"/>'),
  table: svg('<rect x="3" y="4" width="18" height="16" rx="1"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="3" y1="16" x2="21" y2="16"/><line x1="9" y1="4" x2="9" y2="20"/><line x1="15" y1="4" x2="15" y2="20"/>'),
  link: svg('<path d="M10 13a5 5 0 0 0 7.07 0l2.83-2.83a5 5 0 0 0-7.07-7.07l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.07 0L4.1 13.83a5 5 0 0 0 7.07 7.07l1.5-1.5"/>'),
  unlink: svg('<path d="M9 17H7a5 5 0 0 1 0-10h2"/><path d="M15 7h2a5 5 0 0 1 4 8"/><line x1="3" y1="3" x2="21" y2="21"/>'),
  clearFormatting: glyph("T&#215;", "font-size:0.82em"),
  sourceView: svg('<polyline points="8 6 3 12 8 18"/><polyline points="16 6 21 12 16 18"/>'),
  mergeTags: glyph("{&nbsp;}", "font-family:ui-monospace,monospace;font-size:0.9em"),
};
