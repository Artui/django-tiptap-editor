// External-mode version guard. The lossless guarantee is validated against the
// pinned TipTap version baked into the build; under external asset mode the
// consumer can load a different version, so we warn at startup. Consumers can
// set window.DJANGO_TIPTAP_TIPTAP_VERSION (e.g. from their import map) for an
// exact major-mismatch check; otherwise we emit an informational note.
export const SUPPORTED_TIPTAP_VERSION = __DTT_TIPTAP_VERSION__;

const major = (v: string): string => v.split(".")[0];

export function checkTipTapVersion(): void {
  // Only meaningful for the glue (external) build; the bundle pins its own copy.
  if (__DTT_BUILD__ !== "glue") {
    return;
  }
  const loaded = (window as unknown as { DJANGO_TIPTAP_TIPTAP_VERSION?: string })
    .DJANGO_TIPTAP_TIPTAP_VERSION;
  if (loaded && major(loaded) !== major(SUPPORTED_TIPTAP_VERSION)) {
    console.warn(
      `[DjangoTipTap] Loaded TipTap v${loaded} has a different major than the validated ` +
        `v${SUPPORTED_TIPTAP_VERSION}. Markup loss is possible — re-run the fidelity corpus ` +
        `against your TipTap version.`,
    );
    return;
  }
  console.info(
    `[DjangoTipTap] Using an externally-provided TipTap. Lossless behavior was validated ` +
      `against TipTap v${SUPPORTED_TIPTAP_VERSION}; re-run the fidelity corpus against your build.`,
  );
}
