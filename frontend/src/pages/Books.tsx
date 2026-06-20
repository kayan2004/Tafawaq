import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { getToken, getTextbookPdfBlobUrl } from "../lib/api";
import { Icons } from "../lib/icons";

interface Book {
  title: string;
  subtitle: string;
  filename: string;
}

const BOOKS: Book[] = [
  {
    title: "Mathematics — Grade 12",
    subtitle: "Lebanese Official Textbook · Algebra & Geometry",
    filename: "math-gs12-algebra-geometry.pdf",
  },
];

type View =
  | { kind: "library" }
  | { kind: "loading" }
  | { kind: "reader"; pdfUrl: string; book: Book }
  | { kind: "error"; message: string };

type Overlay = { book: Book } | null;

// Must match the CSS transition durations on .book-open-overlay / .book-open-cover.
const FADE_MS = 180;
const ROTATE_MS = 520;

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function Books() {
  const [view, setView] = useState<View>({ kind: "library" });
  const [overlay, setOverlay] = useState<Overlay>(null);
  const [coverOpen, setCoverOpen] = useState(false);
  const [overlayVisible, setOverlayVisible] = useState(false);
  const token = getToken()!;
  const timers = useRef<number[]>([]);

  const schedule = (fn: () => void, ms: number) => {
    const id = window.setTimeout(fn, ms);
    timers.current.push(id);
  };

  useEffect(() => {
    return () => { timers.current.forEach(clearTimeout); };
  }, []);

  // Revoke blob URL on unmount or when leaving reader
  useEffect(() => {
    return () => {
      if (view.kind === "reader") URL.revokeObjectURL(view.pdfUrl);
    };
  }, [view]);

  const openBook = (book: Book) => {
    setView({ kind: "loading" });
    getTextbookPdfBlobUrl(token, book.filename)
      .then((pdfUrl) => setView({ kind: "reader", pdfUrl, book }))
      .catch((err) => setView({ kind: "error", message: err instanceof Error ? err.message : "Failed to load book." }));

    if (prefersReducedMotion()) return;
    setOverlay({ book });
    setCoverOpen(false);
    setOverlayVisible(false);
    requestAnimationFrame(() => setOverlayVisible(true));
    schedule(() => setCoverOpen(true), FADE_MS);
    schedule(() => setOverlayVisible(false), FADE_MS + ROTATE_MS);
    schedule(() => setOverlay(null), FADE_MS + ROTATE_MS + FADE_MS);
  };

  const closeBook = () => {
    const closingBook = view.kind === "reader" ? view.book : null;
    if (view.kind === "reader") URL.revokeObjectURL(view.pdfUrl);

    if (!closingBook || prefersReducedMotion()) {
      setView({ kind: "library" });
      return;
    }
    setOverlay({ book: closingBook });
    setCoverOpen(true);
    setOverlayVisible(false);
    requestAnimationFrame(() => setOverlayVisible(true));
    schedule(() => setCoverOpen(false), FADE_MS);
    schedule(() => setView({ kind: "library" }), FADE_MS + ROTATE_MS);
    schedule(() => setOverlayVisible(false), FADE_MS + ROTATE_MS);
    schedule(() => setOverlay(null), FADE_MS + ROTATE_MS + FADE_MS);
  };

  let content: ReactNode;

  // ── Library ───────────────────────────────────────────────────────────────
  if (view.kind === "library") {
    content = (
      <div className="page">
        <div className="page-head">
          <h1 className="page-title">Books</h1>
          <p className="page-sub">Official Lebanese GS Mathematics textbooks.</p>
        </div>
        <div className="books-library">
          {BOOKS.map((book) => (
            <button key={book.filename} className="books-book-card" onClick={() => openBook(book)}>
              <div className="books-cover">
                <span className="books-cover-symbol">∑</span>
              </div>
              <div className="books-book-info">
                <div className="books-book-title">{book.title}</div>
                <div className="books-book-sub">{book.subtitle}</div>
              </div>
              <div className="books-book-open">
                <Icons.arrow size={18} />
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  } else if (view.kind === "loading") {
    // ── Loading ───────────────────────────────────────────────────────────────
    content = (
      <div className="page">
        <div className="page-head">
          <div className="sk" style={{ height: 28, width: 220, marginBottom: 8 }} />
          <div className="sk" style={{ height: 14, width: 300 }} />
        </div>
        <div className="books-loading-msg">Loading book — this may take a moment…</div>
      </div>
    );
  } else if (view.kind === "error") {
    // ── Error ─────────────────────────────────────────────────────────────────
    content = (
      <div className="page">
        <div className="page-head">
          <h1 className="page-title">Books</h1>
        </div>
        <div className="card" style={{ padding: "32px", maxWidth: 480 }}>
          <p style={{ margin: 0, color: "var(--tier-high)", fontSize: 14 }}>{view.message}</p>
          <button className="btn btn-ghost" style={{ marginTop: 16 }} onClick={() => setView({ kind: "library" })}>
            ← Back
          </button>
        </div>
      </div>
    );
  } else {
    // ── Reader (PDF viewer) ───────────────────────────────────────────────────
    const { pdfUrl, book } = view;
    content = (
      <div className="books-shell">
        <div className="books-reader-bar">
          <button className="btn btn-ghost books-back-btn" onClick={closeBook}>
            ← Books
          </button>
          <div className="books-reader-title">{book.title}</div>
          <div className="books-reader-sub">{book.subtitle}</div>
        </div>
        <iframe
          className="books-pdf-frame"
          src={pdfUrl}
          title={book.title}
        />
      </div>
    );
  }

  return (
    <>
      {content}
      {overlay && (
        <div className={`book-open-overlay ${overlayVisible ? "is-visible" : ""}`}>
          <div className="book-open-stage">
            <div className="book-open-page" />
            <div className={`book-open-cover ${coverOpen ? "is-open" : ""}`}>
              <span className="book-open-cover-symbol">∑</span>
              <span className="book-open-cover-title">{overlay.book.title}</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
