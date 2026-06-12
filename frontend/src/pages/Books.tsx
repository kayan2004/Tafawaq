import { useEffect, useState } from "react";
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

export function Books() {
  const [view, setView] = useState<View>({ kind: "library" });
  const token = getToken()!;

  // Revoke blob URL on unmount or when leaving reader
  useEffect(() => {
    return () => {
      if (view.kind === "reader") URL.revokeObjectURL(view.pdfUrl);
    };
  }, [view]);

  const openBook = async (book: Book) => {
    setView({ kind: "loading" });
    try {
      const pdfUrl = await getTextbookPdfBlobUrl(token, book.filename);
      setView({ kind: "reader", pdfUrl, book });
    } catch (err) {
      setView({ kind: "error", message: err instanceof Error ? err.message : "Failed to load book." });
    }
  };

  const closeBook = () => {
    if (view.kind === "reader") URL.revokeObjectURL(view.pdfUrl);
    setView({ kind: "library" });
  };

  // ── Library ───────────────────────────────────────────────────────────────
  if (view.kind === "library") {
    return (
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
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (view.kind === "loading") {
    return (
      <div className="page">
        <div className="page-head">
          <div className="sk" style={{ height: 28, width: 220, marginBottom: 8 }} />
          <div className="sk" style={{ height: 14, width: 300 }} />
        </div>
        <div className="books-loading-msg">Loading book — this may take a moment…</div>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (view.kind === "error") {
    return (
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
  }

  // ── Reader (PDF viewer) ───────────────────────────────────────────────────
  const { pdfUrl, book } = view;
  return (
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
