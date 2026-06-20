// Config shape carried on the textarea's data-tiptap-config attribute (and the
// Django TIPTAP_DEFAULT_CONFIG setting). The Python side validates structure;
// extension names are resolved here at mount time.
export interface TipTapConfig {
  height?: string;
  locale?: string;
  manualMount?: boolean;
  extensions?: string[];
  linkProtocols?: string[];
  [key: string]: unknown;
}

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
