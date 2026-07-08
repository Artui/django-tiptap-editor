// Built-in toolbar buttons, each backed by a single editor command. Registered
// once at startup; consumers can override any key or add new ones via
// ui.registerButton. Titles are plain labels for now (i18n keys later).
import { configFor } from "../editor-config";
import { translatorFor } from "../i18n";
import { openImagePicker } from "../image-picker";
import type { Editor } from "../tiptap-runtime";
import { insertImage, uploadViaFileDialog } from "../upload";
import { registerButton } from "./button-registry";
import type { ButtonSpec } from "./button-registry";
import { colorControl, commandMenuControl, selectControl } from "./controls";
import type { MenuItem } from "./controls";
import { ICONS } from "./icons";
import { isSourceActive, toggleSourceView } from "./source-view";

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
    title: `heading${level}`,
    isActive: (e: Editor) => e.isActive("heading", { level }),
    onClick: (e: Editor) => e.chain().focus().toggleHeading({ level }).run(),
  };
}

function align(dir: "left" | "center" | "right" | "justify"): ButtonSpec {
  const key = `align${dir[0].toUpperCase()}${dir.slice(1)}`;
  return {
    icon: ICONS[key],
    title: key,
    isActive: (e: Editor) => e.isActive({ textAlign: dir }),
    onClick: (e: Editor) => e.chain().focus().setTextAlign(dir).run(),
  };
}

const BUILTIN: Record<string, ButtonSpec> = {
  undo: {
    icon: ICONS.undo,
    title: "undo",
    isEnabled: (e) => e.can().undo(),
    onClick: (e) => e.chain().focus().undo().run(),
  },
  redo: {
    icon: ICONS.redo,
    title: "redo",
    isEnabled: (e) => e.can().redo(),
    onClick: (e) => e.chain().focus().redo().run(),
  },
  bold: {
    icon: ICONS.bold,
    title: "bold",
    isActive: (e) => e.isActive("bold"),
    onClick: (e) => e.chain().focus().toggleBold().run(),
  },
  italic: {
    icon: ICONS.italic,
    title: "italic",
    isActive: (e) => e.isActive("italic"),
    onClick: (e) => e.chain().focus().toggleItalic().run(),
  },
  underline: {
    icon: ICONS.underline,
    title: "underline",
    isActive: (e) => e.isActive("underline"),
    onClick: (e) => e.chain().focus().toggleUnderline().run(),
  },
  strike: {
    icon: ICONS.strike,
    title: "strike",
    isActive: (e) => e.isActive("strike"),
    onClick: (e) => e.chain().focus().toggleStrike().run(),
  },
  code: {
    icon: ICONS.code,
    title: "code",
    isActive: (e) => e.isActive("code"),
    onClick: (e) => e.chain().focus().toggleCode().run(),
  },
  fontSize: selectControl({
    title: "fontSize",
    attr: "fontSize",
    triggerHTML: `<span class="django-tiptap__glyph">A<small>A</small></span>${caret}`,
    options: (e) =>
      (configFor(e).fontSizes ?? FONT_SIZES).map((v) => ({ label: v.replace("px", ""), value: v })),
  }),
  fontFamily: selectControl({
    title: "fontFamily",
    attr: "fontFamily",
    triggerHTML: `<span class="django-tiptap__glyph">Aa</span>${caret}`,
    options: (e) =>
      (configFor(e).fontFamilies ?? FONT_FAMILIES).map((v) => ({
        label: v.split(",")[0].replace(/'/g, ""),
        value: v,
      })),
    styleOption: true,
  }),
  color: colorControl({
    title: "color",
    attr: "color",
    triggerHTML: `<span class="django-tiptap__glyph django-tiptap__glyph--color">A</span>${caret}`,
    swatches: (e) => configFor(e).textColors ?? TEXT_COLORS,
  }),
  highlight: colorControl({
    title: "highlight",
    attr: "backgroundColor",
    triggerHTML: `<span class="django-tiptap__glyph django-tiptap__glyph--highlight">A</span>${caret}`,
    swatches: (e) => configFor(e).highlightColors ?? HIGHLIGHTS,
  }),
  h1: heading(1),
  h2: heading(2),
  h3: heading(3),
  paragraph: {
    icon: ICONS.paragraph,
    title: "paragraph",
    isActive: (e) => e.isActive("paragraph"),
    onClick: (e) => e.chain().focus().setParagraph().run(),
  },
  bulletList: {
    icon: ICONS.bulletList,
    title: "bulletList",
    isActive: (e) => e.isActive("bulletList"),
    onClick: (e) => e.chain().focus().toggleBulletList().run(),
  },
  orderedList: {
    icon: ICONS.orderedList,
    title: "orderedList",
    isActive: (e) => e.isActive("orderedList"),
    onClick: (e) => e.chain().focus().toggleOrderedList().run(),
  },
  blockquote: {
    icon: ICONS.blockquote,
    title: "blockquote",
    isActive: (e) => e.isActive("blockquote"),
    onClick: (e) => e.chain().focus().toggleBlockquote().run(),
  },
  alignLeft: align("left"),
  alignCenter: align("center"),
  alignRight: align("right"),
  alignJustify: align("justify"),
  image: commandMenuControl({
    title: "image",
    triggerHTML: `${ICONS.image}${caret}`,
    items: (e): MenuItem[] => {
      const cfg = configFor(e);
      const items: MenuItem[] = [
        {
          label: "imageByUrl",
          run: () => {
            const url = window.prompt(translatorFor(e)("imagePrompt"));
            if (url) {
              insertImage(e, url);
            }
          },
        },
      ];
      if (cfg.imageUploadUrl) {
        items.push({ label: "imageUpload", run: () => uploadViaFileDialog(e) });
      }
      if (cfg.imageListUrl) {
        items.push({ label: "imageLibrary", run: () => void openImagePicker(e) });
      }
      return items;
    },
  }),
  mergeTags: commandMenuControl({
    title: "mergeTags",
    triggerHTML: `${ICONS.mergeTags}${caret}`,
    items: (e): MenuItem[] =>
      (configFor(e).mergeTags ?? []).map((tag) => ({
        label: tag.label,
        run: () => e.chain().focus().insertContent(tag.value).run(),
      })),
  }),
  table: commandMenuControl({
    title: "table",
    triggerHTML: `${ICONS.table}${caret}`,
    items: (e): MenuItem[] => {
      const items: MenuItem[] = [
        {
          label: "insertTable",
          run: () => e.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
        },
      ];
      if (e.isActive("table")) {
        items.push(
          "separator",
          { label: "addRowBefore", run: () => e.chain().focus().addRowBefore().run() },
          { label: "addRowAfter", run: () => e.chain().focus().addRowAfter().run() },
          { label: "addColumnBefore", run: () => e.chain().focus().addColumnBefore().run() },
          { label: "addColumnAfter", run: () => e.chain().focus().addColumnAfter().run() },
          "separator",
          { label: "deleteRow", run: () => e.chain().focus().deleteRow().run() },
          { label: "deleteColumn", run: () => e.chain().focus().deleteColumn().run() },
          { label: "deleteTable", run: () => e.chain().focus().deleteTable().run() },
        );
      }
      return items;
    },
  }),
  link: {
    icon: ICONS.link,
    title: "link",
    isActive: (e) => e.isActive("link"),
    onClick: (e) => {
      const prev = (e.getAttributes("link").href as string | undefined) ?? "";
      const url = window.prompt(translatorFor(e)("linkPrompt"), prev);
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
    title: "unlink",
    isEnabled: (e) => e.isActive("link"),
    onClick: (e) => e.chain().focus().extendMarkRange("link").unsetLink().run(),
  },
  clearFormatting: {
    icon: ICONS.clearFormatting,
    title: "clearFormatting",
    onClick: (e) => e.chain().focus().clearNodes().unsetAllMarks().run(),
  },
  sourceView: {
    icon: ICONS.sourceView,
    title: "sourceView",
    isActive: (e) => isSourceActive(e),
    onClick: (e) => toggleSourceView(e),
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
