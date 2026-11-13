"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export default function Home() {
  const { user, isLoading, logout } = useAuth();

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
              Fase 1: Auth & Upload
            </span>
          </div>

          <div className="flex items-center gap-4">
            {!isLoading && (
              <>
                {user ? (
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
                      {user.email}
                    </span>
                    <button
                      onClick={logout}
                      className="text-xs font-medium text-red-600 hover:text-red-700 hover:underline"
                    >
                      Keluar
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-3">
                    <Link
                      href="/login"
                      className="text-sm font-medium text-slate-600 hover:text-slate-900"
                    >
                      Masuk
                    </Link>
                    <Link
                      href="/register"
                      className="text-sm font-semibold px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition"
                    >
                      Daftar Gratis
                    </Link>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-16 flex-1 flex flex-col justify-center">
        <div className="max-w-2xl">
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Pahami Paper Ilmiah Lebih Cepat dan Tervalidasi.
          </h1>
          <p className="mt-4 text-lg text-slate-600 leading-relaxed">
            Asisten riset yang menjawab pertanyaan dari paper ilmiah (PDF atau link arXiv)
            dengan sitasi interaktif yang langsung menyorot teks asli pada dokumen.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              ✓ Sitasi Berbasis Teks Asli
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium bg-blue-50 text-blue-700 border border-blue-200">
              ✓ Anti-Halusinasi (Strict Grounding)
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-md text-sm font-medium bg-purple-50 text-purple-700 border border-purple-200">
              ✓ Ringkasan Terstruktur Otomatis
            </span>
          </div>

          <div className="mt-8">
            {user ? (
              <div className="inline-flex items-center gap-3 px-4 py-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-900">
                <span className="font-semibold text-sm">
                  Selamat datang kembali, {user.email}!
                </span>
                <span className="text-xs text-blue-600">
                  (Fitur upload paper siap dikerjakan di item berikutnya)
                </span>
              </div>
            ) : (
              <Link
                href="/register"
                className="inline-flex items-center justify-center px-6 py-3 text-base font-semibold text-white bg-blue-600 rounded-xl hover:bg-blue-700 shadow-sm transition"
              >
                Mulai Sekarang &mdash; Gratis
              </Link>
            )}
          </div>
        </div>

        <div className="mt-14 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
            <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center font-bold mb-4">
              1
            </div>
            <h3 className="font-semibold text-slate-900 text-base">Unggah Paper</h3>
            <p className="mt-2 text-sm text-slate-500">
              Unggah file PDF (maks. 20 MB) atau tempelkan link/ID arXiv untuk diproses secara asinkron.
            </p>
          </div>

          <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
            <div className="w-10 h-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold mb-4">
              2
            </div>
            <h3 className="font-semibold text-slate-900 text-base">Tanya & Streaming</h3>
            <p className="mt-2 text-sm text-slate-500">
              Ajukan pertanyaan dalam Bahasa Indonesia/Inggris dan dapatkan jawaban mengalir dengan sitasi [1], [2].
            </p>
          </div>

          <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold mb-4">
              3
            </div>
            <h3 className="font-semibold text-slate-900 text-base">Sorot PDF & Verifikasi</h3>
            <p className="mt-2 text-sm text-slate-500">
              Klik tanda sitasi untuk melompat langsung ke halaman dan menyorot kalimat sumber di penampil PDF.
            </p>
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-200 bg-white py-6">
        <div className="max-w-5xl mx-auto px-6 text-center text-xs text-slate-500">
          Telaah &copy; 2026 &mdash; Dibangun dengan Next.js, FastAPI, PostgreSQL + pgvector, dan Gemini.
        </div>
      </footer>
    </div>
  );
}
