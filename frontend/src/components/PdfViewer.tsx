"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import { Citation, getStoredToken } from "@/lib/api";

// Set PDF.js worker
if (typeof window !== "undefined" && !pdfjsLib.GlobalWorkerOptions.workerSrc) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version || "4.10.38"}/build/pdf.worker.min.mjs`;
}

interface HighlightRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PdfViewerProps {
  paperId: string;
  selectedCitation: Citation | null;
  onClearCitation?: () => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function PdfViewer({
  paperId,
  selectedCitation,
  onClearCitation,
}: PdfViewerProps) {
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [userPage, setUserPage] = useState(1);
  const [numPages, setNumPages] = useState(0);
  const [scale, setScale] = useState(1.2);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const renderTaskRef = useRef<pdfjsLib.RenderTask | null>(null);

  // Halaman aktif: Mengikuti sitasi jika ada, atau halaman yang dipilih pengguna
  const currentPage = useMemo(() => {
    if (selectedCitation && selectedCitation.page_start) {
      return Math.max(1, Math.min(selectedCitation.page_start, numPages || 1));
    }
    return Math.max(1, Math.min(userPage, numPages || 1));
  }, [selectedCitation, userPage, numPages]);

  // 1. Muat dokumen PDF dari endpoint backend
  useEffect(() => {
    let isMounted = true;
    const token = getStoredToken();
    const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};

    fetch(`${API_URL}/papers/${paperId}/pdf`, { headers })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Gagal mengunduh file PDF (HTTP ${res.status})`);
        }
        return res.arrayBuffer();
      })
      .then((buffer) => {
        const loadingTask = pdfjsLib.getDocument({
          data: new Uint8Array(buffer),
        });
        return loadingTask.promise;
      })
      .then((doc) => {
        if (isMounted) {
          setPdfDoc(doc);
          setNumPages(doc.numPages);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Gagal membuka PDF:", err);
          setError(err.message || "Gagal memuat dokumen PDF");
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [paperId]);

  // 2. Ekstrak koordinat highlight dari sitasi terpilih
  const extractHighlightRects = useCallback(
    (citation: Citation | null, targetPage: number): HighlightRect[] => {
      if (!citation || !citation.bbox) return [];

      const rawBbox = citation.bbox as unknown;
      const rects: HighlightRect[] = [];

      // Format 1: { boxes: [{ page: number, bbox: [x0, y0, x1, y1] }] }
      if (
        typeof rawBbox === "object" &&
        rawBbox !== null &&
        "boxes" in rawBbox &&
        Array.isArray((rawBbox as { boxes: unknown[] }).boxes)
      ) {
        const boxes = (
          rawBbox as {
            boxes: { page?: number; bbox?: number[] }[];
          }
        ).boxes;
        for (const item of boxes) {
          if (item.page === targetPage && Array.isArray(item.bbox) && item.bbox.length >= 4) {
            const [x0, y0, x1, y1] = item.bbox;
            rects.push({
              x: x0,
              y: y0,
              w: Math.max(x1 - x0, 10),
              h: Math.max(y1 - y0, 10),
            });
          }
        }
        if (rects.length > 0) return rects;
      }

      // Format 2: { x: number, y: number, w: number, h: number }
      if (
        typeof rawBbox === "object" &&
        rawBbox !== null &&
        "x" in rawBbox &&
        "y" in rawBbox
      ) {
        const b = rawBbox as { x: number; y: number; w?: number; h?: number };
        rects.push({
          x: b.x,
          y: b.y,
          w: b.w || 100,
          h: b.h || 20,
        });
        return rects;
      }

      // Format 3: Array langsung [x0, y0, x1, y1]
      if (Array.isArray(rawBbox) && rawBbox.length >= 4) {
        const [x0, y0, x1, y1] = rawBbox as number[];
        rects.push({
          x: x0,
          y: y0,
          w: Math.max(x1 - x0, 10),
          h: Math.max(y1 - y0, 10),
        });
        return rects;
      }

      return rects;
    },
    []
  );

  // Derivasi highlight murni tanpa setState cascading render
  const highlights = useMemo(() => {
    if (!selectedCitation) return [];
    const rawRects = extractHighlightRects(selectedCitation, currentPage);
    return rawRects.map((r) => ({
      x: r.x * scale,
      y: r.y * scale,
      w: r.w * scale,
      h: r.h * scale,
    }));
  }, [selectedCitation, currentPage, scale, extractHighlightRects]);

  // Scroll otomatis ke kotak highlight saat sitasi terpilih berubah
  useEffect(() => {
    if (highlights.length > 0 && containerRef.current) {
      const firstRect = highlights[0];
      containerRef.current.scrollTo({
        top: Math.max(0, firstRect.y - 80),
        behavior: "smooth",
      });
    }
  }, [highlights]);

  // 3. Render halaman ke Canvas dengan PDF.js
  useEffect(() => {
    if (!pdfDoc || currentPage <= 0 || !canvasRef.current) return;

    let isCancelled = false;

    pdfDoc.getPage(currentPage).then((page) => {
      if (isCancelled || !canvasRef.current) return;

      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }

      const viewport = page.getViewport({ scale });
      const canvas = canvasRef.current;
      const context = canvas.getContext("2d");
      if (!context) return;

      canvas.width = viewport.width;
      canvas.height = viewport.height;

      const renderContext = {
        canvasContext: context,
        viewport: viewport,
        canvas: canvas,
      };

      const renderTask = page.render(renderContext);
      renderTaskRef.current = renderTask;

      renderTask.promise.catch((err: unknown) => {
        if (err instanceof Error && err.name !== "RenderingCancelledException") {
          console.error("Gagal merender halaman PDF:", err);
        }
      });
    });

    return () => {
      isCancelled = true;
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }
    };
  }, [pdfDoc, currentPage, scale]);

  // Navigasi kontrol
  const handlePrevPage = () => {
    onClearCitation?.();
    setUserPage((prev) => Math.max(1, prev - 1));
  };

  const handleNextPage = () => {
    onClearCitation?.();
    setUserPage((prev) => Math.min(numPages, prev + 1));
  };

  const handleZoomIn = () => {
    setScale((prev) => Math.min(2.5, +(prev + 0.15).toFixed(2)));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(0.6, +(prev - 0.15).toFixed(2)));
  };

  const handleResetZoom = () => {
    setScale(1.2);
  };

  if (isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center text-slate-500 bg-slate-50">
        <svg className="animate-spin h-8 w-8 text-blue-600 mb-3" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
        </svg>
        <div className="text-sm font-semibold text-slate-700">Memuat Dokumen PDF...</div>
        <div className="text-xs text-slate-400 mt-1">Mengunduh lembaran teks dan layout asli</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center bg-slate-50">
        <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center font-bold mb-2">
          !
        </div>
        <h4 className="text-sm font-bold text-slate-800 mb-1">Tidak Dapat Menampilkan PDF</h4>
        <p className="text-xs text-slate-500 mb-4 max-w-xs">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition"
        >
          Muat Ulang
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-200/70 overflow-hidden select-none">
      {/* Toolbar PDF Viewer */}
      <div className="h-10 border-b border-slate-300 bg-white px-3 flex items-center justify-between text-xs text-slate-700 shrink-0 shadow-sm z-10">
        {/* Navigasi Halaman */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={handlePrevPage}
            disabled={currentPage <= 1}
            title="Halaman Sebelumnya"
            className="p-1 rounded hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent transition text-slate-700 font-bold"
          >
            ◀
          </button>
          <span className="text-xs font-medium text-slate-700">
            Hal. <span className="font-bold">{currentPage}</span> / {numPages}
          </span>
          <button
            onClick={handleNextPage}
            disabled={currentPage >= numPages}
            title="Halaman Berikutnya"
            className="p-1 rounded hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent transition text-slate-700 font-bold"
          >
            ▶
          </button>
        </div>

        {/* Informasi Sitasi Aktif */}
        {selectedCitation && (
          <div className="flex items-center gap-2 bg-amber-50 border border-amber-300 px-2.5 py-0.5 rounded-full text-[11px] font-semibold text-amber-800 animate-pulse">
            <span>
              🎯 Sitasi [{selectedCitation.citation_number}] (Hal. {selectedCitation.page_start || currentPage})
            </span>
            {onClearCitation && (
              <button
                onClick={onClearCitation}
                className="text-amber-700 hover:text-amber-950 ml-1 font-bold"
                title="Hapus Penyorotan"
              >
                ✕
              </button>
            )}
          </div>
        )}

        {/* Kontrol Zoom */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleZoomOut}
            title="Perkecil (-)"
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-slate-100 text-slate-700 font-bold"
          >
            -
          </button>
          <button
            onClick={handleResetZoom}
            title="Reset Zoom"
            className="px-1.5 py-0.5 rounded hover:bg-slate-100 text-[11px] font-semibold text-slate-600"
          >
            {Math.round(scale * 100)}%
          </button>
          <button
            onClick={handleZoomIn}
            title="Perbesar (+)"
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-slate-100 text-slate-700 font-bold"
          >
            +
          </button>
        </div>
      </div>

      {/* Area Canvas PDF dan Overlay Penyorotan (Highlighting) */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-4 flex justify-center items-start relative bg-slate-300/40"
      >
        <div className="relative shadow-xl bg-white border border-slate-300 rounded-sm overflow-hidden">
          {/* Canvas PDF Asli */}
          <canvas ref={canvasRef} className="block" />

          {/* Lapisan Sorot (Highlight Overlay) */}
          <div className="absolute inset-0 pointer-events-none">
            {highlights.map((rect, idx) => (
              <div
                key={idx}
                style={{
                  left: `${rect.x}px`,
                  top: `${rect.y}px`,
                  width: `${rect.w}px`,
                  height: `${rect.h}px`,
                }}
                className="absolute bg-amber-400/35 border-2 border-amber-500 rounded-sm shadow-sm animate-pulse z-20 pointer-events-auto"
                title={
                  selectedCitation
                    ? `Sitasi [${selectedCitation.citation_number}]: ${selectedCitation.snippet}`
                    : "Kutipan Dokumen"
                }
              >
                <span className="absolute -top-5 left-0 px-1 py-0.2 bg-amber-600 text-white text-[9px] font-bold rounded shadow">
                  [{selectedCitation?.citation_number || "Kutipan"}]
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
