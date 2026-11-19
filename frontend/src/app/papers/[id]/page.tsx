"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  Citation,
  ChatMessage,
  getPaper,
  Paper,
  streamPaperChat,
} from "@/lib/api";

function PaperWorkspaceContent() {
  const params = useParams();
  const paperId = params.id as string;
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  const [paper, setPaper] = useState<Paper | null>(null);
  const [isLoadingPaper, setIsLoadingPaper] = useState(true);
  const [paperError, setPaperError] = useState<string | null>(null);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [expandedContexts, setExpandedContexts] = useState<Record<string, boolean>>({});

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const msgCounterRef = useRef(0);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Check auth and load paper
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }

    if (user && paperId) {
      let isMounted = true;
      getPaper(paperId)
        .then((data) => {
          if (isMounted) {
            setPaper(data);
            setIsLoadingPaper(false);
          }
        })
        .catch((err) => {
          if (isMounted) {
            setPaperError(err.message || "Gagal memuat detail paper");
            setIsLoadingPaper(false);
          }
        });

      return () => {
        isMounted = false;
      };
    }
  }, [authLoading, user, paperId, router]);

  // Send message handler
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend ?? inputQuery).trim();
    if (!query || isStreaming || !paperId) return;

    setInputQuery("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    msgCounterRef.current += 1;
    const userMessageId = `user-${msgCounterRef.current}`;
    const assistantMessageId = `asst-${msgCounterRef.current}`;

    // Append user message
    const newMessages: ChatMessage[] = [
      ...messages,
      {
        id: userMessageId,
        role: "user",
        content: query,
      },
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
      },
    ];

    setMessages(newMessages);
    setIsStreaming(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await streamPaperChat(
        paperId,
        query,
        {
          onContext: (chunks) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? { ...m, context_chunks: chunks }
                  : m
              )
            );
          },
          onDelta: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },
          onDone: (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      id: data.message_id || m.id,
                      citations: data.citations,
                      not_found: data.not_found,
                    }
                  : m
              )
            );
          },
          onError: (errMsg) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      content:
                        m.content +
                        `\n\n⚠️ Terjadi kesalahan: ${errMsg}`,
                    }
                  : m
              )
            );
          },
        },
        abortController.signal
      );
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        console.log("Streaming chat dibatalkan oleh pengguna.");
      } else {
        const errorText = err instanceof Error ? err.message : "Gagal menghubungi server";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId
              ? {
                  ...m,
                  content:
                    m.content ||
                    `Maaf, terjadi kesalahan saat menghubungi server: ${errorText}`,
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  };

  const toggleContextAccordion = (msgId: string) => {
    setExpandedContexts((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  // Helper render sitasi bernomor interaktif di teks [1], [2], dst.
  const renderMessageContentWithCitations = (
    text: string,
    citations?: Citation[]
  ) => {
    if (!citations || citations.length === 0) {
      return <span className="whitespace-pre-wrap">{text}</span>;
    }

    // Split teks pada pola [n] atau [n, m]
    const parts = text.split(/(\[[0-9,\s\-]+\])/g);

    return (
      <span className="whitespace-pre-wrap leading-relaxed">
        {parts.map((part, i) => {
          const match = part.match(/^\[([0-9,\s\-]+)\]$/);
          if (match) {
            const rawNums = match[1].split(/[\s,]+/);
            return (
              <span key={i} className="inline-flex items-center gap-0.5 mx-0.5">
                {rawNums.map((nStr, idx) => {
                  const num = parseInt(nStr.trim(), 10);
                  if (isNaN(num)) return null;

                  const cit = citations.find((c) => c.citation_number === num);
                  const isVerified = cit?.verified ?? false;

                  return (
                    <button
                      key={idx}
                      onClick={() => cit && setSelectedCitation(cit)}
                      title={
                        cit
                          ? `Sitasi [${num}]: Bagian ${cit.section || "Umum"} (hlm. ${cit.page_start || "-"})`
                          : `Sitasi [${num}]`
                      }
                      className={`inline-flex items-center justify-center px-1.5 py-0.5 text-[11px] font-bold rounded transition ${
                        isVerified
                          ? "bg-blue-100 text-blue-700 hover:bg-blue-200 border border-blue-300"
                          : "bg-amber-100 text-amber-700 hover:bg-amber-200 border border-amber-300"
                      }`}
                    >
                      [{num}]
                    </button>
                  );
                })}
              </span>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </span>
    );
  };

  if (isLoadingPaper || authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span className="text-sm font-medium text-slate-600">Memuat ruang kerja paper...</span>
        </div>
      </div>
    );
  }

  if (paperError || !paper) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-slate-50 p-6 text-center">
        <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center font-bold mb-3">
          !
        </div>
        <h2 className="text-lg font-bold text-slate-900 mb-1">Paper Tidak Ditemukan</h2>
        <p className="text-sm text-slate-500 mb-5 max-w-md">{paperError || "Paper ini tidak ada atau Anda tidak memiliki akses."}</p>
        <Link
          href="/papers"
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
        >
          Kembali ke Daftar Paper
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-slate-100 overflow-hidden text-slate-900">
      {/* Navbar Atas */}
      <header className="h-14 border-b border-slate-200 bg-white px-4 flex items-center justify-between shrink-0 shadow-sm z-10">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/papers"
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
            title="Kembali ke Daftar Paper"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </Link>
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-slate-900 truncate max-w-xl" title={paper.title || paper.source_ref || "Paper"}>
              {paper.title || paper.source_ref || "Dokumen Ilmiah"}
            </h1>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span>{paper.source_type === "arxiv" ? `arXiv: ${paper.source_ref}` : "PDF Upload"}</span>
              {paper.page_count && (
                <>
                  <span>&bull;</span>
                  <span>{paper.page_count} halaman</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Siap Tanya Jawab
          </span>
        </div>
      </header>

      {/* Main Split Layout: Kiri PDF Viewer, Kanan Chat Interface */}
      <main className="flex flex-1 min-h-0 overflow-hidden">
        {/* Panel Kiri: Wadah PDF Viewer (Akan dihubungkan di item berikutnya) */}
        <section className="hidden md:flex flex-1 flex-col border-r border-slate-200 bg-slate-200/50 relative overflow-hidden">
          <div className="h-10 border-b border-slate-200 bg-white/80 px-4 flex items-center justify-between text-xs text-slate-600 font-medium">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-rose-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
              </svg>
              <span>Dokumen PDF: {paper.source_ref || "paper.pdf"}</span>
            </div>
            {selectedCitation && (
              <span className="text-blue-600 font-semibold bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                Fokus Sitasi [{selectedCitation.citation_number}] (Hal {selectedCitation.page_start || 1})
              </span>
            )}
          </div>

          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
            <div className="w-16 h-16 rounded-2xl bg-white shadow-sm border border-slate-200 flex items-center justify-center mb-4 text-slate-400">
              <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-slate-800 mb-1">
              PDF Viewer Interaktif
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mb-4">
              Komponen PDF.js / react-pdf siap disinkronisasikan. Saat Anda mengklik sitasi bernomor di panel chat kanan, dokumen akan langsung melompat ke halaman terkait dan menyorot teks asli secara presisi.
            </p>
            {selectedCitation && (
              <div className="p-3 bg-white rounded-lg border border-blue-200 text-left max-w-md shadow-sm">
                <div className="text-xs font-bold text-blue-700 mb-1">
                  Cuplikan Sitasi [{selectedCitation.citation_number}] (Bagian: {selectedCitation.section || "Umum"}, Hlm {selectedCitation.page_start})
                </div>
                <p className="text-xs text-slate-600 italic">
                  &ldquo;{selectedCitation.snippet}&rdquo;
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Panel Kanan: Chat Interface dengan Streaming */}
        <section className="flex flex-col w-full md:w-[480px] lg:w-[540px] xl:w-[600px] bg-white border-l border-slate-200 shrink-0">
          {/* Header Chat */}
          <div className="h-10 border-b border-slate-200 px-4 flex items-center justify-between bg-slate-50 shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></div>
              <span className="text-xs font-semibold text-slate-700">Tanya Jawab Paper</span>
            </div>
            {isStreaming && (
              <span className="text-[11px] font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200 animate-pulse">
                Menulis jawaban...
              </span>
            )}
          </div>

          {/* Area Pesan Chat */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
                <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-slate-700 mb-1">
                  Mulai Bertanya tentang Paper Ini
                </h4>
                <p className="text-xs text-slate-500 max-w-xs mb-6">
                  Ajukan pertanyaan apapun seputar metodologi, data, temuan, atau batasan penelitian pada dokumen ini.
                </p>

                {/* Pertanyaan cepat yang disarankan */}
                <div className="w-full space-y-2">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider text-left">
                    Saran Pertanyaan:
                  </div>
                  {[
                    "Apa tujuan dan pertanyaan penelitian utama paper ini?",
                    "Metode dan arsitektur apa yang digunakan?",
                    "Bagaimana hasil eksperimen utama dan kesimpulannya?",
                  ].map((suggested, sIdx) => (
                    <button
                      key={sIdx}
                      onClick={() => handleSendMessage(suggested)}
                      className="w-full text-left p-2.5 rounded-lg border border-slate-200 text-xs text-slate-700 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 transition"
                    >
                      &ldquo;{suggested}&rdquo;
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${
                    msg.role === "user" ? "items-end" : "items-start"
                  }`}
                >
                  <div className="text-[10px] font-semibold text-slate-400 mb-1 px-1">
                    {msg.role === "user" ? "Anda" : "Telaah Asisten"}
                  </div>

                  {/* Bubble Pesan */}
                  <div
                    className={`max-w-[92%] rounded-2xl px-4 py-3 text-xs leading-relaxed shadow-sm ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white rounded-tr-none"
                        : "bg-slate-50 text-slate-800 border border-slate-200 rounded-tl-none"
                    }`}
                  >
                    {/* Indikator "Tidak Ditemukan di Paper" */}
                    {msg.not_found && (
                      <div className="mb-2.5 flex items-center gap-2 p-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-[11px]">
                        <span className="font-bold">⚠️ Informasi Tidak Ditemukan</span>
                        <span className="text-[10px] text-amber-700">
                          (Model menolak berspekulasi di luar dokumen)
                        </span>
                      </div>
                    )}

                    {/* Konten Teks Jawaban dengan Sitasi Bernomor */}
                    {msg.role === "assistant" ? (
                      renderMessageContentWithCitations(msg.content, msg.citations)
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}

                    {/* Animasi Cursor Mengetik Saat Sedang Streaming */}
                    {isStreaming &&
                      msg.role === "assistant" &&
                      msg.id === messages[messages.length - 1]?.id && (
                        <span className="inline-block w-1.5 h-3.5 bg-blue-600 animate-pulse ml-1 align-middle"></span>
                      )}

                    {/* Accordion Konteks yang Digunakan */}
                    {msg.context_chunks && msg.context_chunks.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-200/80">
                        <button
                          onClick={() => toggleContextAccordion(msg.id)}
                          className="flex items-center justify-between w-full text-[11px] font-semibold text-slate-600 hover:text-blue-600 transition"
                        >
                          <span>
                            📚 {msg.context_chunks.length} Potongan Konteks Terambil
                          </span>
                          <span className="text-[10px]">
                            {expandedContexts[msg.id] ? "▲ Tutup" : "▼ Lihat"}
                          </span>
                        </button>

                        {expandedContexts[msg.id] && (
                          <div className="mt-2 space-y-1.5 max-h-48 overflow-y-auto">
                            {msg.context_chunks.map((chunk) => (
                              <div
                                key={chunk.index}
                                className="p-2 rounded bg-white border border-slate-200 text-[11px] text-slate-700"
                              >
                                <div className="flex items-center justify-between font-bold text-blue-700 mb-1">
                                  <span>
                                    [{chunk.index}] {chunk.section?.toUpperCase() || "UMUM"}
                                  </span>
                                  <span className="text-[10px] text-slate-400">
                                    Halaman {chunk.page_start || "-"}
                                  </span>
                                </div>
                                <p className="line-clamp-3 text-slate-600 italic">
                                  &ldquo;{chunk.text}&rdquo;
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Kotak Input Bawah */}
          <div className="p-3 border-t border-slate-200 bg-white shrink-0">
            {isStreaming && (
              <div className="flex items-center justify-between mb-2 px-1">
                <span className="text-xs text-slate-500 italic">
                  Sedang menerima respon streaming...
                </span>
                <button
                  onClick={handleStopStreaming}
                  className="px-2.5 py-1 text-xs font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100 rounded-md border border-rose-200 transition"
                >
                  ⏹ Hentikan Jawaban
                </button>
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-end gap-2 bg-slate-50 rounded-xl border border-slate-200 p-2 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition"
            >
              <textarea
                ref={textareaRef}
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                disabled={isStreaming}
                placeholder="Tanyakan sesuatu tentang isi paper ini... (Enter untuk kirim)"
                rows={1}
                className="flex-1 bg-transparent border-0 resize-none text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none max-h-32 p-1"
              />
              <button
                type="submit"
                disabled={!inputQuery.trim() || isStreaming}
                className="p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:hover:bg-blue-600 transition shrink-0"
                title="Kirim pertanyaan"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </form>
            <div className="text-[10px] text-slate-400 text-center mt-1.5">
              Jawaban dirangkum otomatis dari teks paper dengan sitasi bernomor [1], [2].
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default function PaperWorkspacePage() {
  return (
    <React.Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-slate-50">
          <div className="flex flex-col items-center gap-3">
            <svg className="animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
            </svg>
            <span className="text-sm font-medium text-slate-600">Memuat ruang kerja paper...</span>
          </div>
        </div>
      }
    >
      <PaperWorkspaceContent />
    </React.Suspense>
  );
}
