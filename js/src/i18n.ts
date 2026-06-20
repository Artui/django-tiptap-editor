// Pluggable i18n. en + sv ship built in; consumers add locales at runtime via
// DjangoTipTap.registerLocale(code, strings). Strings are looked up by key with
// fallback to English then the key itself. The active translator per editor is
// resolved from config.locale at mount and stored so any onClick(editor) (and
// the toolbar) can translate without threading `t` everywhere.
import type { Editor } from "./tiptap-runtime";

export type Translator = (key: string) => string;

const EN: Record<string, string> = {
  undo: "Undo",
  redo: "Redo",
  bold: "Bold",
  italic: "Italic",
  underline: "Underline",
  strike: "Strikethrough",
  code: "Inline code",
  heading1: "Heading 1",
  heading2: "Heading 2",
  heading3: "Heading 3",
  paragraph: "Paragraph",
  bulletList: "Bullet list",
  orderedList: "Numbered list",
  blockquote: "Blockquote",
  alignLeft: "Align left",
  alignCenter: "Align center",
  alignRight: "Align right",
  alignJustify: "Justify",
  fontSize: "Font size",
  fontFamily: "Font family",
  color: "Text color",
  highlight: "Highlight",
  image: "Insert image",
  table: "Table",
  link: "Insert or edit link",
  unlink: "Remove link",
  clearFormatting: "Clear formatting",
  sourceView: "Source code",
  default: "Default",
  remove: "Remove",
  insertTable: "Insert table",
  addRowBefore: "Add row above",
  addRowAfter: "Add row below",
  addColumnBefore: "Add column left",
  addColumnAfter: "Add column right",
  deleteRow: "Delete row",
  deleteColumn: "Delete column",
  deleteTable: "Delete table",
  sourceNote: "Editing raw HTML — unsupported markup is normalized when you switch back.",
  linkPrompt: "Link URL",
  imagePrompt: "Image URL",
  imageByUrl: "Insert by URL",
  imageUpload: "Upload…",
  imageLibrary: "From library…",
  mergeTags: "Merge tags",
  pickerTitle: "Select an image",
  pickerEmpty: "No images.",
  pickerError: "Could not load images.",
  close: "Close",
};

const SV: Record<string, string> = {
  undo: "Ångra",
  redo: "Gör om",
  bold: "Fet",
  italic: "Kursiv",
  underline: "Understruken",
  strike: "Genomstruken",
  code: "Infogad kod",
  heading1: "Rubrik 1",
  heading2: "Rubrik 2",
  heading3: "Rubrik 3",
  paragraph: "Stycke",
  bulletList: "Punktlista",
  orderedList: "Numrerad lista",
  blockquote: "Citat",
  alignLeft: "Vänsterjustera",
  alignCenter: "Centrera",
  alignRight: "Högerjustera",
  alignJustify: "Marginaljustera",
  fontSize: "Teckenstorlek",
  fontFamily: "Teckensnitt",
  color: "Textfärg",
  highlight: "Överstrykning",
  image: "Infoga bild",
  table: "Tabell",
  link: "Infoga eller redigera länk",
  unlink: "Ta bort länk",
  clearFormatting: "Rensa formatering",
  sourceView: "Källkod",
  default: "Standard",
  remove: "Ta bort",
  insertTable: "Infoga tabell",
  addRowBefore: "Lägg till rad ovanför",
  addRowAfter: "Lägg till rad nedanför",
  addColumnBefore: "Lägg till kolumn till vänster",
  addColumnAfter: "Lägg till kolumn till höger",
  deleteRow: "Ta bort rad",
  deleteColumn: "Ta bort kolumn",
  deleteTable: "Ta bort tabell",
  sourceNote: "Redigerar rå HTML — okänd markup normaliseras när du växlar tillbaka.",
  linkPrompt: "Länkadress",
  imagePrompt: "Bildadress",
  imageByUrl: "Infoga via URL",
  imageUpload: "Ladda upp…",
  imageLibrary: "Från bibliotek…",
  mergeTags: "Sammanfogningstaggar",
  pickerTitle: "Välj en bild",
  pickerEmpty: "Inga bilder.",
  pickerError: "Kunde inte ladda bilder.",
  close: "Stäng",
};

const locales: Record<string, Record<string, string>> = { en: EN, sv: SV };

export function registerLocale(code: string, strings: Record<string, string>): void {
  locales[code] = { ...(locales[code] ?? {}), ...strings };
}

export function getTranslator(locale: string): Translator {
  return (key: string) => locales[locale]?.[key] ?? EN[key] ?? key;
}

const perEditor = new WeakMap<Editor, Translator>();

export function setTranslator(editor: Editor, translator: Translator): void {
  perEditor.set(editor, translator);
}

export function translatorFor(editor: Editor): Translator {
  return perEditor.get(editor) ?? ((key: string) => EN[key] ?? key);
}
