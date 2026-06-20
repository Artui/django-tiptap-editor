// Extension registry. Consumers register their own TipTap extensions against a
// config name and activate them by listing that name in `config.extensions`
// (and, on the Python side, TIPTAP_EXTRA_EXTENSIONS). Authoring stays a plain
// <script> against the already-loaded library — no bundler of the consumer's
// own — because the building blocks are re-exported on DjangoTipTap.tiptap.
import type { AnyExtension } from "@tiptap/core";

export interface ExtensionContext {
  tiptap: Record<string, unknown>;
  locale: string;
  t: (key: string) => string;
}

export type ExtensionFactory = (
  config: Record<string, unknown>,
  ctx: ExtensionContext,
) => AnyExtension | AnyExtension[];

const factories = new Map<string, ExtensionFactory>();

export function registerExtension(name: string, factory: ExtensionFactory): void {
  factories.set(name, factory);
}

export function getExtensionFactory(name: string): ExtensionFactory | undefined {
  return factories.get(name);
}
