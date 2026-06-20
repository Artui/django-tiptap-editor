// Built-in toolbar buttons, each backed by a single editor command. Registered
// once at startup; consumers can override any key or add new ones via
// ui.registerButton. Titles are plain labels for now (i18n keys later).
import type { Editor } from "../tiptap-runtime";
import { registerButton } from "./button-registry";
import type { ButtonSpec } from "./button-registry";
import { ICONS } from "./icons";

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
