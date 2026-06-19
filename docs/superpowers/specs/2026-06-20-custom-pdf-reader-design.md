# Custom interactive PDF reader — design

## Context

`frontend/src/pages/Books.tsx`'s reader view currently shows the textbook
PDF via a bare `<iframe src={pdfUrl}>` — the browser's native PDF plugin,
with its own (non-themed) toolbar and zoom controls, no integration with
the rest of the app's UI. The user wants something that feels like part
of the product, not an embedded browser plugin.

While exploring `frontend/src/styles/pages.css` for the earlier
book-opening-animation work, a complete *unused* design was found:
`.pdf-stage`, `.pdf-rail` (thumbnail sidebar), `.pdf-pager` (prev/next +
page count), `.pdf-zoom`, `.pdf-page` (styled page surface with
cover/TOC/body treatments). Zero `.tsx` files reference any of these
classes — this is leftover CSS from an earlier mockup, never wired to
real PDF content. Critically, `.pdf-thumb-sheet` is just a plain colored
rectangle with a page-number label (`.pdf-thumb span`) — it was never
designed to hold a real rendered preview image, which simplifies the
rail to a numbered jump-list rather than 258 rendered thumbnails.

The actual textbook PDF (`math-gs12-algebra-geometry.pdf`) is **258
pages, ~30MB** (confirmed by downloading it and counting `/Type /Page`
occurrences). This rules out any approach that eagerly renders or
continuously scrolls all pages at once.

## Scope

**In scope:**
- A new `PdfReader` component that renders one PDF page at a time to a
  `<canvas>` via `pdfjs-dist` (Mozilla's PDF.js core library).
- Page navigation: prev/next buttons + current/total count (`.pdf-pager`),
  a numbered thumbnail rail to jump to any page (`.pdf-rail`/`.pdf-thumb`,
  repurposed as plain numbered buttons, no rendered previews), and
  left/right arrow-key navigation.
- Zoom in/out controls (`.pdf-zoom`), scaling the current page's render.
- Replacing the `<iframe>` in `Books.tsx`'s reader branch with
  `<PdfReader pdfUrl={pdfUrl} title={book.title} />` — everything else in
  `Books.tsx` (the book-opening/closing animation, loading/error states
  for the initial fetch) is unchanged.
- Error handling for: PDF fails to parse, an individual page fails to
  render, with a fallback "open in new tab" link to the raw blob URL.

**Out of scope (deferred, not forgotten):**
- Real rendered page thumbnails in the rail (confirmed unnecessary — the
  original dead CSS never intended this either).
- Continuous-scroll-through-all-pages mode (the dead CSS's `.pdf-scroll`/
  `.pdf-pages` suggested this, but it requires scroll virtualization for
  258 pages — single-page-at-a-time avoids that complexity entirely).
- Text selection/search/copy within the PDF (pdf.js's text layer is
  extra integration work, not requested).
- Mobile touch swipe gestures for page turning.
- Persisting the last-read page across sessions.
- Download/print buttons.
- Any change to `lib/api.ts`'s `getTextbookPdfBlobUrl` — it already
  fetches the PDF with the auth header and returns a blob URL; pdf.js's
  `getDocument({ url })` can consume that blob URL directly, same-origin,
  no changes needed there.

## Architecture

```
Books.tsx (reader branch, unchanged orchestration)
  → <PdfReader pdfUrl={blobUrl} title={book.title} />
       → pdfjs.getDocument({ url: blobUrl }).promise  → PDFDocumentProxy
       → pdfDoc.getPage(currentPage).promise           → PDFPageProxy
       → page.render({ canvasContext, viewport })      → draws to <canvas>
```

`PdfReader` owns all reader-internal state (`currentPage`, `zoom`,
`pdfDoc`, load/render errors) — `Books.tsx` only knows about `pdfUrl` and
`title`, same boundary as the iframe it replaces. The book-opening overlay
animation in `Books.tsx` is untouched; it transitions into whatever the
reader branch renders, regardless of what that is.

**New dependency:** `pdfjs-dist`. Needs one-time Vite worker setup:
```ts
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.mjs?url";
pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;
```
This is the standard Vite-compatible pattern (the `?url` suffix makes
Vite bundle the worker as a served asset and gives back its URL) — no
CDN dependency, no separate build step.

## Components

**`frontend/src/components/PdfReader.tsx`** (new — follows the existing
`components/EditProfileModal.tsx` convention for shared, non-page
components):

- Props: `{ pdfUrl: string; title: string }`.
- State: `pdfDoc: PDFDocumentProxy | null`, `numPages: number`,
  `currentPage: number` (1-indexed), `zoom: number` (default `1`,
  clamped `0.6`–`2`, step `0.2`), `error: string | null`.
- Effect 1 (document load): `pdfjsLib.getDocument({ url: pdfUrl })` on
  mount/`pdfUrl` change; sets `pdfDoc`/`numPages` on success, `error` on
  failure; calls `loadingTask.destroy()` on cleanup.
- Effect 2 (page render): on `pdfDoc`/`currentPage`/`zoom` change, calls
  `pdfDoc.getPage(currentPage)` then `page.render({ canvasContext,
  viewport })` into a `canvasRef`. Keeps the in-flight `RenderTask` in a
  ref and calls `.cancel()` on it before starting a new render — required
  by pdf.js to avoid "rendering already in progress" errors when the user
  clicks next/prev quickly.
- Keyboard handler: `ArrowLeft`/`ArrowRight` change `currentPage` (bounded
  `1..numPages`), attached while the component is mounted.
- Auto-scrolls the active thumbnail into view (`scrollIntoView({ block:
  "nearest" })`) when `currentPage` changes via pager/keyboard rather than
  a thumbnail click.

**Markup** (reusing existing dead CSS classes, now wired to real
behavior):
```
.pdf-stage
  .pdf-rail            → numPages numbered buttons, active = currentPage
  .pdf-canvas-stage    → new class: centers the single rendered page,
                          replaces the dead .pdf-scroll/.pdf-pages pair
                          (those names imply continuous scrolling, which
                          this design explicitly avoids — not reused)
    .pdf-canvas-wrap    → new class: page-surface framing (background,
                          box-shadow) lifted from .pdf-page's existing
                          treatment, sized to the canvas's natural
                          aspect ratio instead of a fixed 620/800 ratio
      <canvas>          → current page render target
.books-reader-bar (existing)
  .pdf-pager            → prev/next + "currentPage / numPages"
  .pdf-zoom              → "−" / "100%" / "+"
```
`.pdf-rail`/`.pdf-pager`/`.pdf-zoom`/`.pdf-stage` already exist in
`pages.css` and are reused as-is. `.pdf-thumb-sheet`'s blank-rectangle
styling is reused as-is for the numbered buttons (just adding `.active`
state styling, which already exists: `.pdf-thumb.active .pdf-thumb-sheet`).
`.pdf-scroll`/`.pdf-pages`/`.pdf-page` (the continuous-scroll-oriented
classes) are left untouched and unused — not repurposed, to avoid a
single-page component sitting under a "scroll" class name.

## Error handling

- **Document fails to load/parse** (`getDocument().promise` rejects):
  show an inline message in place of the canvas — "Couldn't display this
  page the usual way" — with a link `<a href={pdfUrl} target="_blank">
  Open in a new tab</a>` as a fallback to the browser's native viewer.
- **Single page fails to render**: catch the render promise's rejection,
  show a small inline "Couldn't render this page" placeholder inside the
  canvas area, but keep `currentPage`/navigation fully functional so the
  user can move past it.
- **Rapid navigation**: handled by cancelling the in-flight `RenderTask`
  (see Effect 2 above) rather than letting renders race.

## Testing / verification plan

- Manual verification via the running dev stack (same approach used for
  the Topics drill-down and book-opening animation): open the real
  258-page textbook, page forward/back via buttons, arrow keys, and
  thumbnail-rail clicks; zoom in/out; confirm the active thumbnail
  scrolls into view; confirm the book-opening animation still transitions
  correctly into this new reader. Screenshot key states.
- No automated frontend test suite exists in this project (confirmed
  during the Topics drill-down work) — manual browser verification
  remains the verification method for this pass.
- No backend changes — no backend test changes required.
