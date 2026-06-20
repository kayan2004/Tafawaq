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
  const [currentPage, setCurrentPage] = useState(1);
  const [docError, setDocError] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderTaskRef = useRef<RenderTask | null>(null);

  // Load the document
  useEffect(() => {
    let cancelled = false;
    setPdfDoc(null);
    setCurrentPage(1);
    setDocError(null);
    const loadingTask = pdfjsLib.getDocument({ url: pdfUrl });
    loadingTask.promise
      .then((doc) => {
        if (!cancelled) setPdfDoc(doc);
      })
      .catch(() => {
        if (!cancelled) setDocError("Couldn't display this book the usual way.");
      });
    return () => { cancelled = true; loadingTask.destroy(); };
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
      const task = page.render({ canvas, canvasContext: ctx, viewport });
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
