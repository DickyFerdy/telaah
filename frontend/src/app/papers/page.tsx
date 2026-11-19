"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { deletePaper, getPapers, importFromArxiv, Paper, uploadPaper } from "@/lib/api";

function StatusBadge({ paper }: { paper: Paper }) {
  switch (paper.status) {
    case "ready":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          Siap Ditanya
        </span>
      );
    case "parsing":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">
          <svg className="animate-spin h-3 w-3 text-blue-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          Mengekstrak teks...
        </span>
      );
    case "embedding":
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 animate-pulse">
          <svg className="animate-spin h-3 w-3 text-indigo-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          Membuat vektor...
        </span>
      );
    case "failed":
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200"
          title={paper.error_message || "Terjadi kesalahan pemrosesan"}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
          Gagal
        </span>
      );
    case "uploaded":
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
          Diunggah
        </span>
      );
  }
}

export default function PapersPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, logout } = useAuth();

  const [papers, setPapers] = useState<Paper[]>([]);
  const [isLoadingPapers, setIsLoadingPapers] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // arXiv import state
  const [arxivUrl, setArxivUrl] = useState("");
  const [isImportingArxiv, setIsImportingArxiv] = useState(false);
  const [arxivError, setArxivError] = useState<string | null>(null);

  // Deletion state
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadPapers = useCallback(async () => {
    try {
      const data = await getPapers();
      setPapers(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error("Gagal memuat paper:", err.message);
      }
    } finally {
      setIsLoadingPapers(false);
    }
  }, []);

  // Redirect if not logged in and load papers asynchronously
  useEffect(() => {
    let isMounted = true;

    if (!authLoading && !user) {
      router.push("/login");
      return;
    }

    if (user) {
      getPapers()
        .then((data) => {
          if (isMounted) {
            setPapers(data);
            setIsLoadingPapers(false);
          }
        })
        .catch((err: unknown) => {
          if (isMounted) {
            console.error("Gagal memuat paper:", err);
            setIsLoadingPapers(false);
          }
        });
    }

    return () => {
      isMounted = false;
    };
  }, [authLoading, user, router]);

  // Polling for processing status updates
  useEffect(() => {
    const hasPending = papers.some((p) =>
      ["uploaded", "parsing", "embedding"].includes(p.status)
    );
    if (!hasPending) return;

    const interval = setInterval(() => {
      loadPapers();
    }, 4000);

    return () => clearInterval(interval);
  }, [papers, loadPapers]);

  const handleFile = async (file: File) => {
    setUploadError(null);

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Hanya file dengan ekstensi .pdf yang diperbolehkan.");
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setUploadError("Ukuran file tidak boleh melebihi 20 MB.");
      return;
    }

    setIsUploading(true);
    try {
      await uploadPaper(file);
      await loadPapers();
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setUploadError(err.message);
      } else {
        setUploadError("Gagal mengunggah file. Silakan coba lagi.");
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleArxivSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!arxivUrl.trim()) return;

    setIsImportingArxiv(true);
    setArxivError(null);
    try {
      await importFromArxiv(arxivUrl.trim());
      setArxivUrl("");
      await loadPapers();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setArxivError(err.message);
      } else {
        setArxivError("Gagal mengimpor dari arXiv. Silakan coba lagi.");
      }
    } finally {
      setIsImportingArxiv(false);
    }
  };

  const handleDeletePaper = async (paperId: string, paperTitle: string) => {
    const confirmed = window.confirm(
      `Apakah Anda yakin ingin menghapus paper "${paperTitle}"? Semua data ekstraksi dan riwayat chat akan dihapus permanen.`
    );
    if (!confirmed) return;

    setDeletingId(paperId);
    try {
      await deletePaper(paperId);
      await loadPapers();
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert(`Gagal menghapus paper: ${err.message}`);
      } else {
        alert("Gagal menghapus paper. Silakan coba lagi.");
      }
    } finally {
      setDeletingId(null);
    }
  };

  if (authLoading || (!user && authLoading)) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-slate-500 text-sm font-medium">Memuat sesi...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col justify-between">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xl font-bold tracking-tight text-blue-600 hover:opacity-90"
            >
              Telaah
            </Link>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              Dashboard Paper
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/eval"
              className="text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-full border border-indigo-200 transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <span>📊</span>
              <span>Hasil Evaluasi</span>
            </Link>
            <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
              {user?.email}
            </span>
            <button
              onClick={logout}
              className="text-xs font-medium text-red-600 hover:text-red-700 hover:underline"
            >
              Keluar
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10 flex-1 w-full">
        {/* Upload & Import Options */}
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                Daftar Paper Ilmiah
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Unggah file PDF atau impor langsung dari arXiv untuk ditelaah dengan sitasi teks asli.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 1. File Upload Dropzone */}
            <div className="flex flex-col">
              {uploadError && (
                <div className="mb-3 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center justify-between">
                  <span>{uploadError}</span>
                  <button
                    onClick={() => setUploadError(null)}
                    className="text-red-500 hover:text-red-800 font-bold ml-2"
                  >
                    &times;
                  </button>
                </div>
              )}

              <div
                onDragEnter={(e) => {
                  e.preventDefault();
                  setDragActive(true);
                }}
                onDragLeave={(e) => {
                  e.preventDefault();
                  setDragActive(false);
                }}
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex-1 border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center min-h-[180px] ${
                  dragActive
                    ? "border-blue-500 bg-blue-50/50"
                    : "border-slate-300 bg-white hover:border-slate-400 hover:bg-slate-50/50"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFile(e.target.files[0]);
                    }
                  }}
                />

                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-2">
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                </div>

                {isUploading ? (
                  <div className="flex flex-col items-center">
                    <div className="flex items-center gap-2 text-xs font-semibold text-blue-600">
                      <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                      </svg>
                      Mengunggah file...
                    </div>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs font-semibold text-slate-700">
                      <span className="text-blue-600 hover:underline">Unggah PDF</span> atau drag & drop
                    </p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Maksimal 20 MB
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* 2. arXiv Import Card */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col justify-between shadow-sm">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-slate-900">Impor via arXiv</h2>
                    <p className="text-[11px] text-slate-400">Masukkan link abstrak, PDF, atau arXiv ID</p>
                  </div>
                </div>

                {arxivError && (
                  <div className="mb-3 p-2.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center justify-between">
                    <span>{arxivError}</span>
                    <button
                      onClick={() => setArxivError(null)}
                      className="text-red-500 hover:text-red-800 font-bold ml-2"
                    >
                      &times;
                    </button>
                  </div>
                )}
              </div>

              <form onSubmit={handleArxivSubmit} className="mt-4 space-y-2.5">
                <input
                  type="text"
                  value={arxivUrl}
                  onChange={(e) => setArxivUrl(e.target.value)}
                  placeholder="Contoh: 1706.03762 atau https://arxiv.org/abs/..."
                  disabled={isImportingArxiv}
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 focus:bg-white transition"
                />
                <button
                  type="submit"
                  disabled={isImportingArxiv || !arxivUrl.trim()}
                  className="w-full py-2 px-3 text-xs font-semibold rounded-xl bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 transition flex items-center justify-center gap-1.5"
                >
                  {isImportingArxiv ? (
                    <>
                      <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                      </svg>
                      Mengunduh metadata & PDF...
                    </>
                  ) : (
                    "Impor Paper arXiv"
                  )}
                </button>
              </form>
            </div>
          </div>
        </section>

        {/* Papers List */}
        <section>
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900 text-sm">
                Riwayat Paper ({papers.length})
              </h2>
              <button
                onClick={loadPapers}
                className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1"
              >
                ↻ Segarkan
              </button>
            </div>

            {isLoadingPapers ? (
              <div className="p-8 text-center text-sm text-slate-400">
                Memuat daftar paper...
              </div>
            ) : papers.length === 0 ? (
              <div className="p-12 text-center">
                <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
                  📄
                </div>
                <h3 className="text-sm font-semibold text-slate-800">
                  Belum ada paper
                </h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                  Silakan unggah dokumen paper pertama Anda pada kotak di atas untuk memulai tanya jawab.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {papers.map((p) => (
                  <div
                    key={p.id}
                    className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/70 transition"
                  >
                    <div className="flex items-start gap-3.5 min-w-0">
                      <div className="w-9 h-9 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                        PDF
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-sm font-semibold text-slate-900 truncate">
                          {p.title || p.source_ref || "Paper Tanpa Judul"}
                        </h4>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 mt-1">
                          <span>
                            {new Date(p.created_at).toLocaleDateString("id-ID", {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                          <span>&bull;</span>
                          <span>Sumber: {p.source_type}</span>
                          {p.page_count && (
                            <>
                              <span>&bull;</span>
                              <span>{p.page_count} halaman</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                      <StatusBadge paper={p} />
                      {p.status === "ready" && (
                        <Link
                          href={`/papers/${p.id}`}
                          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 transition"
                        >
                          Buka Paper
                        </Link>
                      )}
                      <button
                        onClick={() =>
                          handleDeletePaper(
                            p.id,
                            p.title || p.source_ref || "Paper"
                          )
                        }
                        disabled={deletingId === p.id}
                        title="Hapus paper"
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition disabled:opacity-50"
                      >
                        {deletingId === p.id ? (
                          <svg className="animate-spin h-4 w-4 text-red-600" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white py-6">
        <div className="max-w-5xl mx-auto px-6 text-center text-xs text-slate-500">
          Telaah &copy; 2026 &mdash; Asisten Riset Paper Ilmiah dengan Sitasi Interaktif.
        </div>
      </footer>
    </div>
  );
}
