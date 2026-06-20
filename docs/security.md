# Security

The editor stores HTML and you render it with `|safe`, so the boundary matters. The
design makes `|safe` defensible:

- **ProseMirror's schema is a sanitizer.** Content is parsed into a strict document
  model on load; anything the schema doesn't represent — `<script>`, event handlers,
  unknown tags/attributes — is dropped, not stored. The editor never holds markup it
  can't model.
- **Link protocols are allowlisted** (`linkProtocols`, default `http`/`https`/`mailto`/
  `tel`). `javascript:` and other schemes are stripped on parse.
- **Image `src` is protocol-validated** — both the upload `location` and any picker
  `value` are checked (`http`/`https`/`data`) before insertion; `javascript:` is refused.
- **Source view re-parses through the schema.** Pasting raw HTML into the source view and
  switching back normalizes anything unsupported away — what you see equals what is
  stored.

## What survives

The serialized output is limited to the configured nodes/marks: paragraphs and headings
(with alignment/margin), bold/italic/underline/strike/code, sub/superscript, font
size/family/colour/highlight (as `<span style>`), links (allowlisted), images, tables,
lists, blockquotes, and horizontal rules. Everything else normalizes away.

## Caveats

- **You still control the render context.** `|safe` trusts the *stored* HTML; keep
  untrusted input out of attributes you interpolate around it.
- **Custom extensions own their sanitization.** Any new node/attribute a custom
  extension introduces widens the surface — validate what it accepts.
- **External asset mode** loads TipTap you provide; the guarantees above hold for the
  pinned, bundled version. See [Asset modes](asset-modes.md).
- **Uploads are yours to police.** `BaseImageUploadView` enforces the wire contract, not
  file-type/size/virus policy — add those in `save`.
