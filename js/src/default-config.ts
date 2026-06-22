// Config shape carried on the textarea's data-tiptap-config attribute (and the
// Django TIPTAP_DEFAULT_CONFIG setting). The Python side validates structure;
// extension names are resolved here at mount time.
export interface MergeTag {
  label: string;
  value: string;
}

// Enter / Shift-Enter behaviour. "paragraph" (default) keeps StarterKit's
// semantics; "hardBreak" makes Enter insert a <br>; "swap" exchanges the two.
export type EnterKeyMode = "paragraph" | "hardBreak" | "swap";

export interface TipTapConfig {
  height?: string;
  locale?: string;
  manualMount?: boolean;
  enterKey?: EnterKeyMode;
  extensions?: string[];
  toolbar?: string[][];
  linkProtocols?: string[];
  imageUploadUrl?: string;
  imageListUrl?: string;
  imageFileTypes?: string;
  mergeTags?: MergeTag[];
  // Path B only (passed to init(); not serializable via data-tiptap-config).
  onChange?: (html: string) => void;
  [key: string]: unknown;
}

// Toolbar groups (arrays of button keys). Only buttons backed by a plain
// command are built in so far; richer controls (font size/family, color,
// image, table) arrive with their dropdown UI later.
export const DEFAULT_TOOLBAR: string[][] = [
  ["undo", "redo"],
  ["bold", "italic", "underline", "strike", "code"],
  ["fontSize", "fontFamily", "color", "highlight"],
  ["h1", "h2", "h3", "paragraph"],
  ["bulletList", "orderedList", "blockquote"],
  ["alignLeft", "alignCenter", "alignRight", "alignJustify"],
  ["image", "table"],
  ["link", "unlink", "clearFormatting"],
  ["sourceView"],
];

// Canonical built-in set, in render order. The fidelity layer (margins/indent,
// font-size, background-color highlight, inline image, link) is always present;
// these names let the registry recognise built-ins and let consumers slot
// custom extensions alongside them.
export const DEFAULT_EXTENSIONS: string[] = [
  "bold",
  "italic",
  "underline",
  "strike",
  "code",
  "heading",
  "bulletList",
  "orderedList",
  "listItem",
  "blockquote",
  "horizontalRule",
  "textAlign",
  "fontSize",
  "fontFamily",
  "color",
  "highlight",
  "link",
  "image",
  "table",
  "subscript",
  "superscript",
  "characterCount",
];

export const DEFAULT_LINK_PROTOCOLS: string[] = ["http", "https", "mailto", "tel"];
