# Manual harness

A no-build page for exercising the committed bundle by hand. It mounts editors exactly the
way the Django widget does — a `<textarea>` carrying `data-tiptap-config`, claimed by the
bundle's auto-mount — so what you see here is what a real page does.

```bash
make harness   # serves the repo root at http://localhost:8765/harness/
```

`index.html` loads `django_tiptap_editor/static/` by relative path, so opening the file
directly in a browser works too; the server target exists so the page runs over `http://`
like a real deployment.

Three sections:

- **Playground** — a live editor with an `enterKey` mode switch and the serialized value
  the form would POST, updated on every change.
- **Restricted field** — an email-style field (`features: ["bold", "italic", "link",
  "bulletList", "orderedList"]` with a toolbar to match) above a full one. Type `## `, press
  Ctrl+Alt+2 (Cmd+Option+2 on a Mac), or paste a heading, a table or coloured text into each: the full field keeps
  them, the restricted one keeps only the text, because the excluded nodes and marks are
  not mounted at all. A button per editor pastes through ProseMirror's real clipboard path.
  `js/test/restrict-features.test.ts` is the headless gate for the same routes.
- **Scenarios** — scripted key presses (toolbar click → type → Enter → type) replayed
  across all three `enterKey` modes, each asserting the resulting HTML. Click a `FAIL`
  cell to see expected vs actual. The run also leaves `window.HARNESS_RESULTS` for the
  devtools console.

The scenario grid is a manual mirror of `js/test/enter-key.test.ts`, which runs the same
assertions headlessly in CI. Add a case in both places: the vitest file is the gate, this
page is where you watch it happen in a real browser.

Rebuild the bundle (`make build-js`) after changing anything under `js/src/` — the page
loads the committed artifact, not the sources.
