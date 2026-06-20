// Built-in toolbar buttons, each backed by a single editor command. Registered
// once at startup; consumers can override any key or add new ones via
// ui.registerButton. Titles are plain labels for now (i18n keys later).
import type { Editor } from "../tiptap-runtime";
import { registerButton } from "./button-registry";
import type { ButtonSpec } from "./button-registry";
import { colorControl, selectControl } from "./controls";
import { ICONS } from "./icons";

const FONT_SIZES = ["12px", "14px", "16px", "18px", "24px", "30px", "36px"];
const FONT_FAMILIES = [
  "Arial, sans-serif",
  "Georgia, serif",
  "'Times New Roman', serif",
  "'Courier New', monospace",
  "Verdana, sans-serif",
  "system-ui, sans-serif",
];
const TEXT_COLORS = [
  "#1f2329", "#5c6370", "#e03e2d", "#e8710a", "#f1c40f",
  "#2dc26b", "#3598db", "#3538cd", "#9b59b6", "#ffffff",
];
const HIGHLIGHTS = ["#fff3a3", "#c8f7c5", "#bfe3ff", "#ffd6e7", "#ffe0b2"];

const caret = '<span class="django-tiptap__caret">&#9662;</span>';

function heading(level: 1 | 2 | 3): ButtonSpec {
  return {
    icon: ICONS[`h${level}`],
    title: `Heading ${level}`,
    isActive: (e: Editor) => e.isActive("heading", { level }),
    onClick: (e: Editor) => e.chain().focus().toggleHeading({ level }).run(),
  };
}

function align(dir: "left" | "center" | "right" | "justify"): ButtonSpec {
  const key = `align${dir[0].toUpperCase()}${dir.slice(1)}`;
  return {
    icon: ICONS[key],
    title: `Align ${dir}`,
    isActive: (e: Editor) => e.isActive({ textAlign: dir }),
    onClick: (e: Editor) => e.chain().focus().setTextAlign(dir).run(),
  };
}

const BUILTIN: Record<string, ButtonSpec> = {
  undo: {
    icon: ICONS.undo,
    title: "Undo",
    isEnabled: (e) => e.can().undo(),
    onClick: (e) => e.chain().focus().undo().run(),
  },
  redo: {
    icon: ICONS.redo,
    title: "Redo",
    isEnabled: (e) => e.can().redo(),
    onClick: (e) => e.chain().focus().redo().run(),
  },
  bold: {
    icon: ICONS.bold,
    title: "Bold",
    isActive: (e) => e.isActive("bold"),
    onClick: (e) => e.chain().focus().toggleBold().run(),
  },
  italic: {
    icon: ICONS.italic,
    title: "Italic",
    isActive: (e) => e.isActive("italic"),
    onClick: (e) => e.chain().focus().toggleItalic().run(),
  },
  underline: {
    icon: ICONS.underline,
    title: "Underline",
    isActive: (e) => e.isActive("underline"),
    onClick: (e) => e.chain().focus().toggleUnderline().run(),
  },
  strike: {
    icon: ICONS.strike,
    title: "Strikethrough",
    isActive: (e) => e.isActive("strike"),
    onClick: (e) => e.chain().focus().toggleStrike().run(),
  },
  code: {
    icon: ICONS.code,
    title: "Inline code",
    isActive: (e) => e.isActive("code"),
    onClick: (e) => e.chain().focus().toggleCode().run(),
  },
  fontSize: selectControl({
    title: "Font size",
    attr: "fontSize",
    triggerHTML: `<span class="django-tiptap__glyph">A<small>A</small></span>${caret}`,
    options: FONT_SIZES.map((v) => ({ label: v.replace("px", ""), value: v })),
  }),
  fontFamily: selectControl({
    title: "Font family",
    attr: "fontFamily",
    triggerHTML: `<span class="django-tiptap__glyph">Aa</span>${caret}`,
    options: FONT_FAMILIES.map((v) => ({ label: v.split(",")[0].replace(/'/g, ""), value: v })),
    styleOption: true,
  }),
  color: colorControl({
    title: "Text color",
    attr: "color",
    triggerHTML: `<span class="django-tiptap__glyph django-tiptap__glyph--color">A</span>${caret}`,
    swatches: TEXT_COLORS,
  }),
  highlight: colorControl({
    title: "Highlight",
    attr: "backgroundColor",
    triggerHTML: `<span class="django-tiptap__glyph django-tiptap__glyph--highlight">A</span>${caret}`,
    swatches: HIGHLIGHTS,
  }),
  h1: heading(1),
  h2: heading(2),
  h3: heading(3),
  paragraph: {
    icon: ICONS.paragraph,
    title: "Paragraph",
    isActive: (e) => e.isActive("paragraph"),
    onClick: (e) => e.chain().focus().setParagraph().run(),
  },
  bulletList: {
    icon: ICONS.bulletList,
    title: "Bullet list",
    isActive: (e) => e.isActive("bulletList"),
    onClick: (e) => e.chain().focus().toggleBulletList().run(),
  },
  orderedList: {
    icon: ICONS.orderedList,
    title: "Numbered list",
    isActive: (e) => e.isActive("orderedList"),
    onClick: (e) => e.chain().focus().toggleOrderedList().run(),
  },
  blockquote: {
    icon: ICONS.blockquote,
    title: "Blockquote",
    isActive: (e) => e.isActive("blockquote"),
    onClick: (e) => e.chain().focus().toggleBlockquote().run(),
  },
  alignLeft: align("left"),
  alignCenter: align("center"),
  alignRight: align("right"),
  alignJustify: align("justify"),
  link: {
    icon: ICONS.link,
    title: "Insert / edit link",
    isActive: (e) => e.isActive("link"),
    onClick: (e) => {
      const prev = (e.getAttributes("link").href as string | undefined) ?? "";
      const url = window.prompt("Link URL", prev);
      if (url === null) {
        return;
      }
      if (url === "") {
        e.chain().focus().extendMarkRange("link").unsetLink().run();
        return;
      }
      e.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
    },
  },
  unlink: {
    icon: ICONS.unlink,
    title: "Remove link",
    isEnabled: (e) => e.isActive("link"),
    onClick: (e) => e.chain().focus().extendMarkRange("link").unsetLink().run(),
  },
  clearFormatting: {
    icon: ICONS.clearFormatting,
    title: "Clear formatting",
    onClick: (e) => e.chain().focus().clearNodes().unsetAllMarks().run(),
  },
};

let registered = false;

export function registerBuiltInButtons(): void {
  if (registered) {
    return;
  }
  for (const [key, spec] of Object.entries(BUILTIN)) {
    registerButton(key, spec);
  }
  registered = true;
}
