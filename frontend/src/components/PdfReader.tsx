import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.mjs?url";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

const BASE_SCALE = 1.4;
const MIN_ZOOM = 0.6;
const MAX_ZOOM = 2;
const ZOOM_STEP = 0.2;

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
  const [zoom, setZoom] = useState(1);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderTaskRef = useRef<RenderTask | null>(null);
  const activeThumbRef = useRef<HTMLButtonElement>(null);
  const navSourceRef = useRef<"thumb" | "other">("other");

  useEffect(() => {
    setPdfDoc(null);
    setNumPages(0);
    setCurrentPage(1);
    setDocError(null);
    let cancelled = false;
    const loadingTask = pdfjsLib.getDocument({ url: pdfUrl });
    loadingTask.promise
      .then((doc) => {
        if (cancelled) return;
        setPdfDoc(doc);
        setNumPages(doc.numPages);
      })
      .catch(() => {
        if (cancelled) return;
        setDocError("Couldn't display this book the usual way.");
      });
    return () => { cancelled = true; loadingTask.destroy(); };
  }, [pdfUrl]);

  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;
    setPageError(null);
    let cancelled = false;

    pdfDoc.getPage(currentPage).then((page) => {
      if (cancelled || !canvasRef.current) return;
      const viewport = page.getViewport({ scale: BASE_SCALE * zoom });
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      renderTaskRef.current?.cancel();
      const task = page.render({ canvasContext: ctx, viewport, canvas });
      renderTaskRef.current = task;
      task.promise.catch((err: { name?: string }) => {
        if (err?.name !== "RenderingCancelledException") {
          setPageError("Couldn't render this page.");
        }
      });
    });

    return () => { cancelled = true; renderTaskRef.current?.cancel(); };
  }, [pdfDoc, currentPage, zoom]);

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

  useEffect(() => {
    if (navSourceRef.current === "thumb") { navSourceRef.current = "other"; return; }
    activeThumbRef.current?.scrollIntoView({ block: "nearest" });
  }, [currentPage]);

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
        <div className="pdf-zoom">
          <button onClick={() => setZoom((z) => Math.max(MIN_ZOOM, +(z - ZOOM_STEP).toFixed(1)))} disabled={zoom <= MIN_ZOOM} aria-label="Zoom out">−</button>
          <span>{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom((z) => Math.min(MAX_ZOOM, +(z + ZOOM_STEP).toFixed(1)))} disabled={zoom >= MAX_ZOOM} aria-label="Zoom in">+</button>
        </div>
      </div>
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
          <div className="pdf-canvas-wrap">
            <canvas ref={canvasRef} className="pdf-canvas" aria-label={`${title}, page ${currentPage}`} />
            {pageError && <div className="pdf-canvas-error">{pageError}</div>}
          </div>
        </div>
      </div>
    </>
  );
}
