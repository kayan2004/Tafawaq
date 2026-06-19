# Custom Interactive PDF Reader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bare `<iframe>` textbook viewer in `Books.tsx` with a themed, interactive page-by-page PDF reader (page nav, thumbnail jump-list, zoom), rendered via `pdfjs-dist`.

**Architecture:** A new `PdfReader` component loads the PDF with `pdfjs-dist`, renders the current page to a `<canvas>`, and exposes pager/zoom/thumbnail-rail controls built on CSS classes (`.pdf-stage`, `.pdf-rail`, `.pdf-thumb`, `.pdf-pager`, `.pdf-zoom`) that already exist in `pages.css` but were never wired to real markup. `Books.tsx`'s reader branch swaps `<iframe src={pdfUrl}>` for `<PdfReader pdfUrl={pdfUrl} title={book.title} />` — nothing else in `Books.tsx` changes.

**Tech Stack:** React 19 + TypeScript, Vite, `pdfjs-dist` v6 (new dependency).

## Global Constraints

- No automated frontend test suite exists in this project (no test files, no `test` script in `package.json` — confirmed during this same project's earlier Topics-drill-down work). **This plan substitutes "Manual browser verification" steps for the template's automated test steps** — every task still ends in an independently checkable deliverable, verified by actually opening the app in a browser, per this project's established verification convention (used for the Topics drill-down and book-opening-animation features earlier this session).
- `pdfjs-dist`'s worker must be wired via Vite's `?url` import suffix: `import workerUrl from "pdfjs-dist/build/pdf.worker.mjs?url"` then `pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl`. **Verified working** against the real 258-page textbook PDF in this session (smoke-tested, then reverted) — use this exact pattern, do not deviate.
- The textbook PDF is 258 pages / ~30MB. Never render more than the current page's canvas at once — no eager rendering of all pages, no continuous-scroll-of-everything.
- `.pdf-scroll`/`.pdf-pages`/`.pdf-page` (existing dead CSS) are **not** reused — those names imply continuous scrolling, which this design avoids. New classes (`.pdf-canvas-stage`, `.pdf-canvas-wrap`) are added instead.
- `.pdf-rail`/`.pdf-pager`/`.pdf-zoom`/`.pdf-stage`/`.pdf-thumb`/`.pdf-thumb-sheet` (existing dead CSS) **are** reused as-is; `.pdf-thumb` needs one small addition (button-reset styles) since it was authored as a plain `<div>` target, not a clickable button.
- Dev environment note: this Windows/Git-Bash environment has a `/tmp` path mismatch between tools — write any test/scratch files inside the repo directory, never `/tmp/...`.
- `npm install --no-save <pkg>` calls are destructive to each other (each invocation's dependency-reconciliation pass silently removes previously-not-saved packages not listed in `package.json`/lockfile) — if a task needs a temporary throwaway package alongside `pdfjs-dist` for manual verification, install both in one `npm install --no-save` command, never sequential calls.
- Never run `git add -A`/`git add .`; stage exact files only. Never commit `Co-Authored-By` (CLAUDE.md hard rule already established this session).

---

### Task 1: Add `pdfjs-dist`, create `PdfReader` rendering a single page, wire into `Books.tsx`

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json` (real `npm install`, saved this time)
- Create: `frontend/src/components/PdfReader.tsx`
- Modify: `frontend/src/styles/pages.css` (add `.pdf-canvas-stage`, `.pdf-canvas-wrap`, `.pdf-canvas`, `.pdf-canvas-error`, `.pdf-toolbar`; add button-reset to existing `.pdf-thumb`)
- Modify: `frontend/src/pages/Books.tsx:1-4,160-164` (import `PdfReader`, replace the `<iframe>`)

**Interfaces:**
- Produces: `PdfReader` component, props `{ pdfUrl: string; title: string }`. No other task/file calls into its internals — `Books.tsx` only ever renders `<PdfReader pdfUrl={pdfUrl} title={book.title} />`.

- [ ] **Step 1: Install `pdfjs-dist`**

```bash
cd frontend
npm install pdfjs-dist
```

Expected: `package.json` now has `"pdfjs-dist": "^6.x.x"` under `dependencies`; `package-lock.json` updated.

- [ ] **Step 2: Create `frontend/src/components/PdfReader.tsx`**

```tsx
import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.mjs?url";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

const BASE_SCALE = 1.4;

interface PdfReaderProps {
  pdfUrl: string;
  title: string;
}

export function PdfReader({ pdfUrl, title }: PdfReaderProps) {
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [docError, setDocError] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderTaskRef = useRef<RenderTask | null>(null);

  // Load the document
  useEffect(() => {
    setPdfDoc(null);
    setNumPages(0);
    setCurrentPage(1);
    setDocError(null);
    const loadingTask = pdfjsLib.getDocument({ url: pdfUrl });
    loadingTask.promise
      .then((doc) => {
        setPdfDoc(doc);
        setNumPages(doc.numPages);
      })
      .catch(() => setDocError("Couldn't display this book the usual way."));
    return () => { loadingTask.destroy(); };
  }, [pdfUrl]);

  // Render the current page
  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;
    setPageError(null);
    let cancelled = false;

    pdfDoc.getPage(currentPage).then((page) => {
      if (cancelled || !canvasRef.current) return;
      const viewport = page.getViewport({ scale: BASE_SCALE });
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      renderTaskRef.current?.cancel();
      const task = page.render({ canvasContext: ctx, viewport });
      renderTaskRef.current = task;
      task.promise.catch((err: { name?: string }) => {
        if (err?.name !== "RenderingCancelledException") {
          setPageError("Couldn't render this page.");
        }
      });
    });

    return () => { cancelled = true; renderTaskRef.current?.cancel(); };
  }, [pdfDoc, currentPage]);

  if (docError) {
    return (
      <div className="pdf-stage" style={{ alignItems: "center", justifyContent: "center" }}>
        <div className="card" style={{ padding: 32, maxWidth: 420, textAlign: "center" }}>
          <p style={{ margin: "0 0 12px", color: "var(--tier-high)", fontSize: 14 }}>{docError}</p>
          <a href={pdfUrl} target="_blank" rel="noreferrer" className="btn btn-ghost">
            Open in a new tab
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="pdf-stage">
      <div className="pdf-canvas-stage">
        <div className="pdf-canvas-wrap">
          <canvas ref={canvasRef} className="pdf-canvas" aria-label={`${title}, page ${currentPage}`} />
          {pageError && <div className="pdf-canvas-error">{pageError}</div>}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add CSS to `frontend/src/styles/pages.css`**

Add directly after the existing `.pdf-line { ... }` rule (the last rule in the dead "PDF components" block, just before the `/* PDF iframe (existing books view) */` comment):

```css
.pdf-toolbar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 10px 16px;
  background: var(--bg-tint);
  border-bottom: 1px solid var(--line); flex-shrink: 0;
}
.pdf-canvas-stage { flex: 1; overflow: auto; display: flex; justify-content: center; padding: 24px 0 60px; background: var(--pdf-gutter); }
.pdf-canvas-wrap { box-shadow: 0 8px 30px rgba(0,0,0,0.5); height: fit-content; }
.pdf-canvas { display: block; background: #fbfbf8; }
.pdf-canvas-error {
  position: absolute; inset: 0; display: grid; place-items: center;
  background: rgba(0,0,0,0.6); color: #fff; font-size: 13px; text-align: center; padding: 16px;
}
.pdf-thumb { background: none; border: none; padding: 0; cursor: pointer; }
```

Note: `.pdf-canvas-wrap` needs `position: relative` for `.pdf-canvas-error`'s `position: absolute` to anchor correctly — add it to the same rule: `.pdf-canvas-wrap { position: relative; box-shadow: ...; height: fit-content; }`.

- [ ] **Step 4: Wire `PdfReader` into `Books.tsx`**

In `frontend/src/pages/Books.tsx`, change line 4 from:
```tsx
import { Icons } from "../lib/icons";
```
to:
```tsx
import { Icons } from "../lib/icons";
import { PdfReader } from "../components/PdfReader";
```

Then replace (around line 160-164):
```tsx
        <iframe
          className="books-pdf-frame"
          src={pdfUrl}
          title={book.title}
        />
```
with:
```tsx
        <PdfReader pdfUrl={pdfUrl} title={book.title} />
```

- [ ] **Step 5: Manual browser verification**

Start the dev server (`cd frontend && npm run dev -- --port 5180`), add `'/textbook': 'http://localhost:8000'` temporarily to `vite.config.ts`'s proxy block (the dev proxy is missing this route — production nginx already has it, confirmed earlier this session), register a test user via `POST /auth/register` + `POST /auth/jwt/login` + `PUT /auth/me/details` (same pattern used for every other manual verification this session), open the Books page, click the book, and confirm:
- The book-opening animation still plays (unchanged).
- A real rendered page (not blank, not an iframe) appears — note page 1 of this textbook is a near-blank title page, so check page contains visible content by temporarily setting `currentPage` initial state to e.g. `15` if needed to eyeball real content, then revert that temporary change.
- No console errors.

Revert the temporary `vite.config.ts` proxy addition and delete any throwaway test users/DB rows afterward (`DELETE FROM user_details WHERE user_id = ...` then `DELETE FROM users WHERE email = ...`).

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/PdfReader.tsx frontend/src/styles/pages.css frontend/src/pages/Books.tsx
git commit -m "feat(books): render textbook pages via pdfjs-dist instead of an iframe"
```

---

### Task 2: Page navigation — pager buttons + arrow keys + render cancellation

**Files:**
- Modify: `frontend/src/components/PdfReader.tsx`

**Interfaces:**
- Consumes: `numPages`, `currentPage`, `setCurrentPage`, `renderTaskRef` (all already defined in Task 1).
- Produces: a `goToPage(n: number)` function clamped to `1..numPages`, used by Task 3 (thumbnail rail) too.

- [ ] **Step 1: Add the pager toolbar and keyboard navigation**

Replace the full contents of `frontend/src/components/PdfReader.tsx` with:

```tsx
import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.mjs?url";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

const BASE_SCALE = 1.4;

interface PdfReaderProps {
  pdfUrl: string;
  title: string;
}

export function PdfReader({ pdfUrl, title }: PdfReaderProps) {
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [docError, setDocError] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderTaskRef = useRef<RenderTask | null>(null);

  useEffect(() => {
    setPdfDoc(null);
    setNumPages(0);
    setCurrentPage(1);
    setDocError(null);
    const loadingTask = pdfjsLib.getDocument({ url: pdfUrl });
    loadingTask.promise
      .then((doc) => {
        setPdfDoc(doc);
        setNumPages(doc.numPages);
      })
      .catch(() => setDocError("Couldn't display this book the usual way."));
    return () => { loadingTask.destroy(); };
  }, [pdfUrl]);

  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;
    setPageError(null);
    let cancelled = false;

    pdfDoc.getPage(currentPage).then((page) => {
      if (cancelled || !canvasRef.current) return;
      const viewport = page.getViewport({ scale: BASE_SCALE });
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      renderTaskRef.current?.cancel();
      const task = page.render({ canvasContext: ctx, viewport });
      renderTaskRef.current = task;
      task.promise.catch((err: { name?: string }) => {
        if (err?.name !== "RenderingCancelledException") {
          setPageError("Couldn't render this page.");
        }
      });
    });

    return () => { cancelled = true; renderTaskRef.current?.cancel(); };
  }, [pdfDoc, currentPage]);

  const goToPage = (n: number) => {
    if (n < 1 || n > numPages) return;
    setCurrentPage(n);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") goToPage(currentPage - 1);
      if (e.key === "ArrowRight") goToPage(currentPage + 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [currentPage, numPages]);

  if (docError) {
    return (
      <div className="pdf-stage" style={{ alignItems: "center", justifyContent: "center" }}>
        <div className="card" style={{ padding: 32, maxWidth: 420, textAlign: "center" }}>
          <p style={{ margin: "0 0 12px", color: "var(--tier-high)", fontSize: 14 }}>{docError}</p>
          <a href={pdfUrl} target="_blank" rel="noreferrer" className="btn btn-ghost">
            Open in a new tab
          </a>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="pdf-toolbar">
        <div className="pdf-pager">
          <button onClick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1} aria-label="Previous page">‹</button>
          <span className="pdf-pager-count">{currentPage} <small>/ {numPages || "…"}</small></span>
          <button onClick={() => goToPage(currentPage + 1)} disabled={currentPage >= numPages} aria-label="Next page">›</button>
        </div>
      </div>
      <div className="pdf-stage">
        <div className="pdf-canvas-stage">
          <div className="pdf-canvas-wrap">
            <canvas ref={canvasRef} className="pdf-canvas" aria-label={`${title}, page ${currentPage}`} />
            {pageError && <div className="pdf-canvas-error">{pageError}</div>}
          </div>
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 2: Manual browser verification**

Using the same temporary dev-proxy + test-user setup as Task 1 Step 5: open the book, click next/prev repeatedly (including rapid clicking, to exercise render cancellation), use the left/right arrow keys, confirm the "X / 258" counter updates correctly and buttons disable at page 1 and page 258. Check the console for "rendering already in progress" errors (there should be none — that's what `renderTaskRef.current?.cancel()` prevents). Clean up the temporary proxy change and test user afterward.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PdfReader.tsx
git commit -m "feat(books): add page-by-page navigation with arrow-key support"
```

---

### Task 3: Thumbnail rail (numbered jump-list) with auto-scroll-into-view

**Files:**
- Modify: `frontend/src/components/PdfReader.tsx`

**Interfaces:**
- Consumes: `numPages`, `currentPage`, `goToPage` (from Task 2).
- Produces: no new exports — purely additive UI within the same component.

- [ ] **Step 1: Add the rail**

In `frontend/src/components/PdfReader.tsx`, add two new refs right after the existing `renderTaskRef` declaration:

```tsx
  const activeThumbRef = useRef<HTMLButtonElement>(null);
  const navSourceRef = useRef<"thumb" | "other">("other");
```

Add a new effect right after the keyboard-navigation effect (after its closing `}, [currentPage, numPages]);`):

```tsx
  useEffect(() => {
    if (navSourceRef.current === "thumb") { navSourceRef.current = "other"; return; }
    activeThumbRef.current?.scrollIntoView({ block: "nearest" });
  }, [currentPage]);
```

Replace the `return (` JSX block's `.pdf-stage` section — change:
```tsx
      <div className="pdf-stage">
        <div className="pdf-canvas-stage">
```
to:
```tsx
      <div className="pdf-stage">
        <div className="pdf-rail">
          {Array.from({ length: numPages }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              ref={n === currentPage ? activeThumbRef : undefined}
              className={`pdf-thumb${n === currentPage ? " active" : ""}`}
              onClick={() => { navSourceRef.current = "thumb"; goToPage(n); }}
            >
              <span className="pdf-thumb-sheet" />
              <span>{n}</span>
            </button>
          ))}
        </div>
        <div className="pdf-canvas-stage">
```

- [ ] **Step 2: Manual browser verification**

Open the book, click several thumbnails in the rail and confirm the main canvas jumps to that page and the `.active` outline moves correctly. Then use next/prev buttons and arrow keys and confirm the rail auto-scrolls to keep the active thumbnail visible (`scrollIntoView`). Confirm clicking a thumbnail does *not* cause a redundant scroll-jump within the rail itself (the `navSourceRef` guard).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PdfReader.tsx
git commit -m "feat(books): add thumbnail rail for jumping to any page"
```

---

### Task 4: Zoom controls

**Files:**
- Modify: `frontend/src/components/PdfReader.tsx`

**Interfaces:**
- Consumes: nothing new from other tasks.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Add zoom state and controls**

Add constants near the top of `frontend/src/components/PdfReader.tsx`, alongside `BASE_SCALE`:

```tsx
const MIN_ZOOM = 0.6;
const MAX_ZOOM = 2;
const ZOOM_STEP = 0.2;
```

Add a `zoom` state declaration alongside the other `useState` calls:

```tsx
  const [zoom, setZoom] = useState(1);
```

Change the page-render effect's viewport line from:
```tsx
      const viewport = page.getViewport({ scale: BASE_SCALE });
```
to:
```tsx
      const viewport = page.getViewport({ scale: BASE_SCALE * zoom });
```
and add `zoom` to that effect's dependency array: `}, [pdfDoc, currentPage, zoom]);`

Add the zoom toolbar markup inside `.pdf-toolbar`, right after the closing `</div>` of `.pdf-pager`:
```tsx
        <div className="pdf-zoom">
          <button onClick={() => setZoom((z) => Math.max(MIN_ZOOM, +(z - ZOOM_STEP).toFixed(1)))} disabled={zoom <= MIN_ZOOM} aria-label="Zoom out">−</button>
          <span>{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom((z) => Math.min(MAX_ZOOM, +(z + ZOOM_STEP).toFixed(1)))} disabled={zoom >= MAX_ZOOM} aria-label="Zoom in">+</button>
        </div>
```

- [ ] **Step 2: Manual browser verification**

Open the book, click zoom in/out several times, confirm the canvas resizes and stays sharp (not blurry — pdf.js re-renders at the new scale rather than CSS-scaling a fixed-resolution canvas), confirm buttons disable at the 60%/200% bounds, confirm the percentage label updates.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PdfReader.tsx
git commit -m "feat(books): add zoom controls to the PDF reader"
```

---

### Task 5: Error-handling polish (doc-load failure verification)

**Files:**
- Modify: `frontend/src/components/PdfReader.tsx` (no code change expected — this task is verification-only, confirming behavior already implemented in Task 1)

The doc-load-failure (`docError`) and per-page-render-failure (`pageError`) paths were already implemented in Task 1's initial component. This task verifies both actually work, since neither has been exercised yet (the smoke test and Tasks 1-4 only ever hit the success path).

**Interfaces:**
- Consumes: `docError`, `pageError` (already defined in Task 1).
- Produces: nothing new.

- [ ] **Step 1: Verify the doc-load-failure path**

Temporarily edit `frontend/src/pages/Books.tsx`'s `openBook` function to pass a deliberately-broken URL to `PdfReader` for this check only (e.g., temporarily change the reader branch to `<PdfReader pdfUrl="blob:invalid" title={book.title} />`), reload, open the book, and confirm the "Couldn't display this book the usual way." message + "Open in a new tab" link render correctly in place of the canvas. Revert the temporary change immediately after confirming.

- [ ] **Step 2: Verify the per-page-render-failure path stays non-fatal**

This is harder to force without corrupting a real PDF page, so verify by code review instead: confirm in `frontend/src/components/PdfReader.tsx` that `pageError` is only ever set inside the `task.promise.catch(...)` handler (never thrown/rethrown), and that `pageError` rendering (`{pageError && <div className="pdf-canvas-error">...}`) is layered via `position: absolute` over the canvas rather than replacing it — so `currentPage`/pager/rail/zoom remain interactive even if one page's render fails.

- [ ] **Step 3: Commit (if any revert cleanup is needed)**

```bash
git status --short
```
Expected: clean except for any earlier-task commits already made — Task 5 makes no lasting code changes, only verifies Task 1's existing error paths. If `git status` shows changes, they are leftover temporary edits from Step 1 that must be reverted, not committed.

---

## Self-Review Notes

- **Spec coverage:** Single-page canvas rendering (Task 1), pager + keyboard nav (Task 2), thumbnail rail + auto-scroll (Task 3), zoom (Task 4), error handling for doc-load and per-page failures (Task 1 implements both, Task 5 verifies both) — all spec sections covered. The spec's explicit non-goals (real thumbnail previews, continuous scroll, text selection, mobile swipe, persisted last-page, download/print) have no corresponding tasks, correctly.
- **Type consistency:** `goToPage`, `currentPage`, `numPages`, `pdfDoc`, `canvasRef`, `renderTaskRef` are introduced in Task 1/2 and referenced identically (same names) in Tasks 3-4 — checked against each task's full-file code blocks above.
- **`.pdf-canvas-wrap` `position: relative`** is called out explicitly in Task 1 Step 3 (needed for `.pdf-canvas-error`'s absolute positioning) rather than left implicit.
