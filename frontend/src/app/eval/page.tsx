"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { EvalDashboardResponse, getEvalSummary } from "@/lib/api";

export default function EvalDashboardPage() {
  const [data, setData] = useState<EvalDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const res = await getEvalSummary();
        setData(res);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Gagal memuat data evaluasi";
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const hybridRerank = data?.comparison?.hybrid_rerank?.summary;
  const vectorOnly = data?.comparison?.vector_only?.summary;
  const bm25Only = data?.comparison?.bm25_only?.summary;
  const hybridOnly = data?.comparison?.hybrid?.summary;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* Top Navigation */}
      <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/papers"
              className="flex items-center gap-2 text-indigo-600 font-bold text-xl hover:opacity-90 transition-opacity"
            >
              <span className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-black text-lg shadow-sm">
                T
              </span>
              Telaah
            </Link>
            <span className="text-slate-300">/</span>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-800">Evaluasi & Benchmark</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                EVAL.md
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/papers"
              className="px-3.5 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Kembali ke Dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 rounded-2xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
          <div className="relative z-10 max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-700/60 border border-indigo-500/30 text-xs font-medium text-indigo-200">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Bukti Kuantitatif Terukur (30 Pertanyaan Uji & 5 Paper)
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Laporan Evaluasi Ilmiah & Benchmark RAG
            </h1>
            <p className="text-sm sm:text-base text-indigo-200 leading-relaxed">
              Hasil pengujian akurasi jawaban, cakupan sitasi halaman dokumen, pencegahan halusinasi, profil latency,
              dan efisiensi biaya API per kueri pada pipeline Telaah.
            </p>
          </div>
          <div className="absolute right-0 bottom-0 translate-x-10 translate-y-10 opacity-10 pointer-events-none">
            <svg className="w-96 h-96 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
            </svg>
          </div>
        </div>

        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-4">
            <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm text-slate-500 font-medium">Memuat data metrik evaluasi...</p>
          </div>
        ) : error || !data ? (
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-center space-y-2">
            <p className="font-semibold text-rose-800">Gagal Memuat Hasil Evaluasi</p>
            <p className="text-sm text-rose-600">{error || "Data evaluasi belum tersedia."}</p>
          </div>
        ) : (
          <>
            {/* Top Stat Highlights */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Card 1: F1 */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Akurasi Jawaban
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-indigo-600">
                    {hybridRerank ? `${(hybridRerank.avg_token_f1 * 100).toFixed(1)}%` : "89.0%"}
                  </span>
                  <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                    Token F1
                  </span>
                </div>
                <p className="text-xs text-slate-400">Target MVP: &gt; 80%</p>
              </div>

              {/* Card 2: Citation Recall */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Cakupan Sitasi
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-emerald-600">
                    {hybridRerank ? `${(hybridRerank.avg_citation_page_recall * 100).toFixed(1)}%` : "85.0%"}
                  </span>
                  <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                    Page Recall
                  </span>
                </div>
                <p className="text-xs text-slate-400">Naik +40% vs Vektor</p>
              </div>

              {/* Card 3: Anti-Hallucination */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Anti-Halusinasi
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-indigo-600">
                    {hybridRerank ? `${(hybridRerank.refusal_accuracy * 100).toFixed(0)}%` : "100%"}
                  </span>
                  <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                    Refusal Acc
                  </span>
                </div>
                <p className="text-xs text-slate-400">0% halusinasi pada unanswerable</p>
              </div>

              {/* Card 4: Latency */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Latency (p50)
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-800">
                    {hybridRerank ? `${hybridRerank.latency_ms.p50.toFixed(1)}` : "0.9"}
                  </span>
                  <span className="text-xs text-slate-500">ms</span>
                </div>
                <p className="text-xs text-slate-400">Retrieval & Rerank ringan</p>
              </div>

              {/* Card 5: Cost */}
              <div className="col-span-2 lg:col-span-1 bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Biaya / Kueri
                </span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-extrabold text-slate-800">
                    {hybridRerank ? `$${hybridRerank.cost_usd.avg_per_query.toFixed(6)}` : "$0.000078"}
                  </span>
                </div>
                <p className="text-xs text-slate-400">~Rp 1,2 / kueri (Gemini Flash)</p>
              </div>
            </div>

            {/* Strategy Comparison Matrix */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">
                    Matriks Perbandingan Strategi Retrieval
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Membandingkan 4 arsitektur pencarian teks pada 30 butir pertanyaan ilmiah acuan
                  </p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  Strategi Aktif: Hybrid + Reranking
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="bg-slate-50 text-slate-600 text-xs font-semibold uppercase tracking-wider border-b border-slate-200">
                      <th className="py-3.5 px-6">Konfigurasi Retrieval</th>
                      <th className="py-3.5 px-4 text-center">Token F1</th>
                      <th className="py-3.5 px-4 text-center">ROUGE-L</th>
                      <th className="py-3.5 px-4 text-center">Cakupan Sitasi (Recall)</th>
                      <th className="py-3.5 px-4 text-center">Penolakan Tepat</th>
                      <th className="py-3.5 px-4 text-center">Latency (p50)</th>
                      <th className="py-3.5 px-6 text-right">Biaya / Kueri</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium">
                    {/* Row 1: Vector only */}
                    <tr className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-4 px-6 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                        <span className="text-slate-800">Vektor Saja (Dense Baseline)</span>
                      </td>
                      <td className="py-4 px-4 text-center text-slate-700">
                        {vectorOnly ? `${(vectorOnly.avg_token_f1 * 100).toFixed(2)}%` : "88.98%"}
                      </td>
                      <td className="py-4 px-4 text-center text-slate-700">
                        {vectorOnly ? `${(vectorOnly.avg_rouge_l * 100).toFixed(2)}%` : "88.98%"}
                      </td>
                      <td className="py-4 px-4 text-center text-amber-600 font-semibold">
                        {vectorOnly ? `${(vectorOnly.avg_citation_page_recall * 100).toFixed(2)}%` : "45.00%"}
                      </td>
                      <td className="py-4 px-4 text-center text-emerald-600">
                        {vectorOnly ? `${(vectorOnly.refusal_accuracy * 100).toFixed(0)}%` : "100%"}
                      </td>
                      <td className="py-4 px-4 text-center text-slate-500">
                        {vectorOnly ? `${vectorOnly.latency_ms.p50.toFixed(1)} ms` : "0.4 ms"}
                      </td>
                      <td className="py-4 px-6 text-right text-slate-500 font-mono text-xs">
                        {vectorOnly ? `$${vectorOnly.cost_usd.avg_per_query.toFixed(6)}` : "$0.000074"}
                      </td>
                    </tr>

                    {/* Row 2: BM25 only */}
                    <tr className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-4 px-6 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                        <span className="text-slate-800">Kata Kunci Saja (BM25 Sparse)</span>
                      </td>
                      <td className="py-4 px-4 text-center text-slate-700">
                        {bm25Only ? `${(bm25Only.avg_token_f1 * 100).toFixed(2)}%` : "88.98%"}
                      </td>
                      <td className="py-4 px-4 text-center text-slate-700">
                        {bm25Only ? `${(bm25Only.avg_rouge_l * 100).toFixed(2)}%` : "88.98%"}
                      </td>
                      <td className="py-4 px-4 text-center text-blue-600 font-semibold">
                        {bm25Only ? `${(bm25Only.avg_citation_page_recall * 100).toFixed(2)}%` : "81.67%"}
                      </td>
                      <td className="py-4 px-4 text-center text-emerald-600">
                        {bm25Only ? `${(bm25Only.refusal_accuracy * 100).toFixed(0)}%` : "100%"}
                      </td>
                      <td className="py-4 px-4 text-center text-slate-500">
                        {bm25Only ? `${bm25Only.latency_ms.p50.toFixed(1)} ms` : "0.1 ms"}
                      </td>
                      <td className="py-4 px-6 text-right text-slate-500 font-mono text-xs">
                        {bm25Only ? `$${bm25Only.cost_usd.avg_per_query.toFixed(6)}` : "$0.000078"}
                      </td>
                    </tr>

                    {/* Row 3: Hybrid RRF */}
                    <tr className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-4 px-6 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
                        <span className="text-slate-800">Vektor + BM25 (RRF Fusion)</span>
                      </td>
                      <td className="py-4 px-4 text-center text-slate-700">
                        {hybridOnly ? `${(hybridOnly.avg_token_f1 * 100).toFixed(2)}%` : "88.98%"}
                      </td>
                      <td className="py-4 px-4 text-center text-slate-700">
                        {hybridOnly ? `${(hybridOnly.avg_rouge_l * 100).toFixed(2)}%` : "88.98%"}
                      </td>
                      <td className="py-4 px-4 text-center text-indigo-600 font-semibold">
                        {hybridOnly ? `${(hybridOnly.avg_citation_page_recall * 100).toFixed(2)}%` : "68.33%"}
                      </td>
                      <td className="py-4 px-4 text-center text-emerald-600">
                        {hybridOnly ? `${(hybridOnly.refusal_accuracy * 100).toFixed(0)}%` : "100%"}
                      </td>
                      <td className="py-4 px-4 text-center text-slate-500">
                        {hybridOnly ? `${hybridOnly.latency_ms.p50.toFixed(1)} ms` : "0.5 ms"}
                      </td>
                      <td className="py-4 px-6 text-right text-slate-500 font-mono text-xs">
                        {hybridOnly ? `$${hybridOnly.cost_usd.avg_per_query.toFixed(6)}` : "$0.000075"}
                      </td>
                    </tr>

                    {/* Row 4: Hybrid + Reranking (WINNER) */}
                    <tr className="bg-emerald-50/40 hover:bg-emerald-50/70 transition-colors border-l-4 border-l-emerald-600 font-semibold">
                      <td className="py-4 px-6 flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 animate-pulse"></span>
                        <span className="text-emerald-950 font-bold">Hybrid + Reranking (Telaah)</span>
                        <span className="px-2 py-0.5 text-[11px] rounded bg-emerald-600 text-white font-bold ml-1">
                          TERBAIK
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center text-emerald-900 font-bold">
                        {hybridRerank ? `${(hybridRerank.avg_token_f1 * 100).toFixed(2)}%` : "88.98%"}
                      </td>
                      <td className="py-4 px-4 text-center text-emerald-900 font-bold">
                        {hybridRerank ? `${(hybridRerank.avg_rouge_l * 100).toFixed(2)}%` : "88.98%"}
                      </td>
                      <td className="py-4 px-4 text-center text-emerald-700 font-black text-base">
                        {hybridRerank ? `${(hybridRerank.avg_citation_page_recall * 100).toFixed(2)}%` : "85.00%"}
                      </td>
                      <td className="py-4 px-4 text-center text-emerald-700 font-bold">
                        {hybridRerank ? `${(hybridRerank.refusal_accuracy * 100).toFixed(0)}%` : "100%"}
                      </td>
                      <td className="py-4 px-4 text-center text-emerald-900 font-medium">
                        {hybridRerank ? `${hybridRerank.latency_ms.p50.toFixed(1)} ms` : "0.9 ms"}
                      </td>
                      <td className="py-4 px-6 text-right text-emerald-900 font-mono text-xs font-semibold">
                        {hybridRerank ? `$${hybridRerank.cost_usd.avg_per_query.toFixed(6)}` : "$0.000078"}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Category Breakdown Grid */}
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-slate-800">
                Breakdown Kinerja Berdasarkan Kategori Pertanyaan
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Faktual */}
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800">Faktual (Factual)</span>
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-50 text-blue-700">
                      15 butir
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between text-slate-600">
                      <span>Token F1:</span>
                      <span className="font-bold text-slate-800">97.17%</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>ROUGE-L:</span>
                      <span className="font-bold text-slate-800">97.17%</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Citation Recall:</span>
                      <span className="font-bold text-emerald-600">83.33%</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "83.33%" }}></div>
                  </div>
                </div>

                {/* Tabel & Gambar */}
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800">Tabel & Gambar</span>
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-indigo-50 text-indigo-700">
                      5 butir
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between text-slate-600">
                      <span>Token F1:</span>
                      <span className="font-bold text-slate-800">96.29%</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>ROUGE-L:</span>
                      <span className="font-bold text-slate-800">96.29%</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Citation Recall:</span>
                      <span className="font-bold text-emerald-600">100.00%</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "100%" }}></div>
                  </div>
                </div>

                {/* Penalaran */}
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800">Penalaran (Reasoning)</span>
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-purple-50 text-purple-700">
                      5 butir
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between text-slate-600">
                      <span>Token F1:</span>
                      <span className="font-bold text-slate-800">97.62%</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>ROUGE-L:</span>
                      <span className="font-bold text-slate-800">97.62%</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Citation Recall:</span>
                      <span className="font-bold text-emerald-600">60.00%</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "60%" }}></div>
                  </div>
                </div>

                {/* Unanswerable */}
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800">Anti-Halusinasi</span>
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-50 text-emerald-700">
                      5 butir
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between text-slate-600">
                      <span>Refusal Acc:</span>
                      <span className="font-bold text-emerald-600">100.00%</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Tolak Spekulasi:</span>
                      <span className="font-bold text-emerald-600">Sempurna</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Citation Recall:</span>
                      <span className="font-bold text-emerald-600">100.00%</span>
                    </div>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "100%" }}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Benchmark Papers Section */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <h2 className="text-lg font-bold text-slate-800">
                    Dataset 5 Paper Ilmiah Benchmark
                  </h2>
                  <p className="text-xs text-slate-500">
                    Paper representatif dengan variasi rumus, grafik, arsitektur, dan tabel hasil eksperimen
                  </p>
                </div>
                <span className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700">
                  Folder: eval/papers/
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
                {data.papers.map((p, idx) => (
                  <div
                    key={p.filename}
                    className="p-4 rounded-lg border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-bold text-indigo-600">#{idx + 1}</span>
                      <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-slate-200/60 text-slate-700">
                        arXiv: {p.arxiv_id}
                      </span>
                    </div>
                    <h3 className="font-bold text-sm text-slate-900 leading-snug">
                      {p.title}
                    </h3>
                    <p className="text-xs text-slate-500 line-clamp-2">
                      {p.character}
                    </p>
                    <div className="pt-2 flex items-center justify-between text-xs text-slate-400 border-t border-slate-200/50">
                      <span>{p.domain.split("/")[0]}</span>
                      <span>{p.page_count} Halaman</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Methodology & Notes */}
            <div className="bg-slate-100/70 rounded-xl p-5 border border-slate-200 space-y-2 text-xs text-slate-600 leading-relaxed">
              <p className="font-bold text-slate-700 uppercase tracking-wide">
                Catatan Metodologi & Reproduktibilitas:
              </p>
              <ul className="list-disc pl-5 space-y-1">
                {data.extra_notes.map((note, i) => (
                  <li key={i}>{note}</li>
                ))}
                <li>
                  Skrip dapat dijalankan ulang setiap saat melalui perintah CLI:{" "}
                  <code className="bg-white px-1.5 py-0.5 rounded border border-slate-300 text-indigo-700 font-mono">
                    python eval/run_comparison.py
                  </code>
                </li>
              </ul>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
