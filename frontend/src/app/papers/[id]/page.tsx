"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import PdfViewer from "@/components/PdfViewer";
import {
  Citation,
  ChatMessage,
  ConversationItem,
  deleteConversation,
  explainPaperTerm,
  ExplainTermResponse,
  generatePaperSummary,
  getConversationMessages,
  getPaper,
  getPaperConversations,
  getPaperSummary,
  Paper,
  regeneratePaperSummary,
  streamPaperChat,
  SummaryResponse,
} from "@/lib/api";

function PaperWorkspaceContent() {
  const params = useParams();
  const paperId = params.id as string;
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  const [paper, setPaper] = useState<Paper | null>(null);
  const [isLoadingPaper, setIsLoadingPaper] = useState(true);
  const [paperError, setPaperError] = useState<string | null>(null);

  // Tab state (Chat vs Summary)
  const [activeTab, setActiveTab] = useState<"chat" | "summary">("chat");

  // Summary state
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  // Term explainer state (fitur seleksi teks)
  const [selectedTerm, setSelectedTerm] = useState<string>("");
  const [termContext, setTermContext] = useState<string>("");
  const [tooltipPosition, setTooltipPosition] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [isExplainingTerm, setIsExplainingTerm] = useState(false);
  const [explainedData, setExplainedData] =
    useState<ExplainTermResponse | null>(null);
  const [showExplainModal, setShowExplainModal] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [expandedContexts, setExpandedContexts] = useState<Record<string, boolean>>({});

  // Conversations history state
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [showHistoryDropdown, setShowHistoryDropdown] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

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

  // Load conversations list
  const refreshConversations = async () => {
    if (!paperId) return;
    try {
      const list = await getPaperConversations(paperId);
      setConversations(list);
    } catch (err) {
      console.error("Gagal memperbarui riwayat percakapan:", err);
    }
  };

  // Check auth and load paper & conversations
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

      getPaperConversations(paperId)
        .then(async (list) => {
          if (!isMounted) return;
          setConversations(list);
          if (list.length > 0) {
            const latest = list[0];
            setCurrentConversationId(latest.id);
            const msgs = await getConversationMessages(paperId, latest.id);
            if (isMounted) {
              setMessages(msgs);
            }
          }
        })
        .catch((err) => {
          console.error("Gagal memuat riwayat percakapan:", err);
        });

      getPaperSummary(paperId)
        .then((sumData) => {
          if (isMounted) {
            setSummary(sumData);
          }
        })
        .catch(() => {
          // Ringkasan belum dibuat untuk paper ini, normal
        });

      return () => {
        isMounted = false;
      };
    }
  }, [authLoading, user, paperId, router]);

  // Handler ekstraksi / regenerasi ringkasan
  const handleGenerateSummary = async (isRegenerate = false) => {
    if (!paperId || isGeneratingSummary) return;
    setIsGeneratingSummary(true);
    setSummaryError(null);
    try {
      const res = isRegenerate
        ? await regeneratePaperSummary(paperId)
        : await generatePaperSummary(paperId);
      setSummary(res);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Gagal menghasilkan ringkasan paper";
      setSummaryError(msg);
    } finally {
      setIsGeneratingSummary(false);
    }
  };

  // Deteksi seleksi teks di layar untuk penjelasan istilah
  useEffect(() => {
    const handleMouseUp = () => {
      setTimeout(() => {
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed) {
          setTooltipPosition(null);
          return;
        }

        const text = selection.toString().trim();
        const words = text.split(/\s+/).filter(Boolean);
        // Tampilkan tombol jelaskan istilah jika teks antara 1 s.d. 15 kata
        if (text.length >= 2 && words.length >= 1 && words.length <= 15) {
          try {
            const range = selection.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            const nodeText =
              range.commonAncestorContainer.textContent || text;

            setSelectedTerm(text);
            setTermContext(nodeText.slice(0, 500));
            setTooltipPosition({
              x: Math.max(20, rect.left + rect.width / 2),
              y: Math.max(10, rect.top - 10),
            });
          } catch {
            setTooltipPosition(null);
          }
        } else {
          setTooltipPosition(null);
        }
      }, 50);
    };

    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const handleExplainTerm = async () => {
    if (!selectedTerm || !paperId) return;
    setTooltipPosition(null);
    setShowExplainModal(true);
    setIsExplainingTerm(true);
    setExplainedData(null);
    try {
      const res = await explainPaperTerm(paperId, selectedTerm, termContext);
      setExplainedData(res);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Gagal menjelaskan istilah";
      setExplainedData({
        term: selectedTerm,
        explanation: `Terjadi kendala saat menjelaskan istilah: ${msg}`,
      });
    } finally {
      setIsExplainingTerm(false);
    }
  };

  // Conversation switching handlers
  const handleNewConversation = () => {
    setCurrentConversationId(null);
    setMessages([]);
    setSelectedCitation(null);
    setShowHistoryDropdown(false);
  };

  const handleSelectConversation = async (convId: string) => {
    if (convId === currentConversationId) {
      setShowHistoryDropdown(false);
      return;
    }
    setIsLoadingHistory(true);
    setShowHistoryDropdown(false);
    try {
      const msgs = await getConversationMessages(paperId, convId);
      setCurrentConversationId(convId);
      setMessages(msgs);
      setSelectedCitation(null);
    } catch (err) {
      console.error("Gagal memuat pesan percakapan:", err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleDeleteConversation = async (
    e: React.MouseEvent,
    convId: string
  ) => {
    e.stopPropagation();
    try {
      await deleteConversation(paperId, convId);
      const updated = conversations.filter((c) => c.id !== convId);
      setConversations(updated);
      if (currentConversationId === convId) {
        if (updated.length > 0) {
          handleSelectConversation(updated[0].id);
        } else {
          handleNewConversation();
        }
      }
    } catch (err) {
      console.error("Gagal menghapus percakapan:", err);
    }
  };

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
            if (data.conversation_id) {
              setCurrentConversationId(data.conversation_id);
              refreshConversations();
            }
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
        abortController.signal,
        currentConversationId
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
        {/* Panel Kiri: PDF Viewer Interaktif dengan Sitasi */}
        <section className="hidden md:flex flex-1 flex-col border-r border-slate-200 bg-slate-200/50 relative overflow-hidden">
          <PdfViewer
            paperId={paperId}
            selectedCitation={selectedCitation}
            onClearCitation={() => setSelectedCitation(null)}
          />
        </section>

        {/* Panel Kanan: Chat Interface dengan Streaming */}
        <section className="flex flex-col w-full md:w-[480px] lg:w-[540px] xl:w-[600px] bg-white border-l border-slate-200 shrink-0">
          {/* Header Tab Switcher */}
          <div className="h-11 border-b border-slate-200 px-3 flex items-center justify-between bg-slate-50 shrink-0 relative">
            <div className="flex items-center gap-1 bg-slate-200/70 p-0.5 rounded-lg">
              <button
                type="button"
                onClick={() => setActiveTab("chat")}
                className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition ${
                  activeTab === "chat"
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
                <span>Tanya Jawab</span>
                {isStreaming && (
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></span>
                )}
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("summary")}
                className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md transition ${
                  activeTab === "summary"
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <span>Ringkasan</span>
                {summary && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                )}
              </button>
            </div>

            {/* Kontrol Kanan Spesifik Tiap Tab */}
            {activeTab === "chat" ? (
              <div className="flex items-center gap-1.5">
                {/* Tombol Riwayat Percakapan (Dropdown) */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowHistoryDropdown((prev) => !prev)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border transition ${
                      showHistoryDropdown
                        ? "bg-slate-200 border-slate-300 text-slate-900"
                        : "bg-white border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                    title="Riwayat Percakapan"
                  >
                    <svg
                      className="w-3.5 h-3.5 text-slate-500"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <span>Riwayat</span>
                    {conversations.length > 0 && (
                      <span className="px-1.5 py-0.2 text-[10px] font-semibold bg-slate-100 text-slate-600 rounded-full border border-slate-200">
                        {conversations.length}
                      </span>
                    )}
                  </button>

                  {/* Dropdown Menu Riwayat */}
                  {showHistoryDropdown && (
                    <div className="absolute right-0 mt-1 w-72 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-30 max-h-80 overflow-y-auto">
                      <div className="px-3 py-1.5 border-b border-slate-100 flex items-center justify-between">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                          Sesi Diskusi ({conversations.length})
                        </span>
                        <button
                          onClick={() => setShowHistoryDropdown(false)}
                          className="text-slate-400 hover:text-slate-600 text-xs"
                        >
                          ✕
                        </button>
                      </div>

                      {isLoadingHistory ? (
                        <div className="p-4 text-center text-xs text-slate-400">
                          Memuat sesi...
                        </div>
                      ) : conversations.length === 0 ? (
                        <div className="p-4 text-center text-xs text-slate-400">
                          Belum ada riwayat percakapan.
                        </div>
                      ) : (
                        conversations.map((conv) => (
                          <div
                            key={conv.id}
                            onClick={() => handleSelectConversation(conv.id)}
                            className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-50 flex items-start justify-between gap-2 border-b border-slate-50 cursor-pointer ${
                              conv.id === currentConversationId
                                ? "bg-blue-50/70 border-l-2 border-l-blue-600"
                                : ""
                            }`}
                          >
                            <div className="min-w-0 flex-1">
                              <p className="font-medium text-slate-800 truncate">
                                {conv.preview || "Percakapan Baru"}
                              </p>
                              <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400">
                                <span>{conv.message_count} pesan</span>
                                <span>&bull;</span>
                                <span>
                                  {new Date(conv.created_at).toLocaleDateString(
                                    "id-ID",
                                    {
                                      month: "short",
                                      day: "numeric",
                                    }
                                  )}
                                </span>
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={(e) => handleDeleteConversation(e, conv.id)}
                              className="p-1 text-slate-300 hover:text-rose-500 rounded transition"
                              title="Hapus sesi ini"
                            >
                              <svg
                                className="w-3.5 h-3.5"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth="2"
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                />
                              </svg>
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>

                {/* Tombol Percakapan Baru */}
                <button
                  type="button"
                  onClick={handleNewConversation}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 transition shadow-sm"
                  title="Mulai Percakapan Baru"
                >
                  <svg
                    className="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                  <span>Baru</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                {summary && (
                  <button
                    type="button"
                    onClick={() => handleGenerateSummary(true)}
                    disabled={isGeneratingSummary}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition shadow-xs disabled:opacity-50"
                    title="Buat Ulang Ringkasan"
                  >
                    <svg
                      className={`w-3.5 h-3.5 text-slate-500 ${
                        isGeneratingSummary ? "animate-spin" : ""
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                      />
                    </svg>
                    <span>{isGeneratingSummary ? "Memproses..." : "Buat Ulang"}</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Body Panel: Ringkasan Terstruktur VS Tanya Jawab Chat */}
          {activeTab === "summary" ? (
            <div className="flex-1 p-5 overflow-y-auto space-y-4 bg-slate-50/50">
              {summaryError && (
                <div className="p-3 text-xs bg-rose-50 border border-rose-200 text-rose-700 rounded-lg flex items-center justify-between">
                  <span>⚠️ {summaryError}</span>
                  <button
                    onClick={() => setSummaryError(null)}
                    className="text-rose-400 hover:text-rose-600 text-sm font-bold ml-2"
                  >
                    ✕
                  </button>
                </div>
              )}

              {isGeneratingSummary && !summary ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500">
                  <svg
                    className="animate-spin h-8 w-8 text-blue-600 mb-3"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v8H4z"
                    ></path>
                  </svg>
                  <h4 className="text-sm font-semibold text-slate-800 mb-1">
                    Sedang Mengekstrak Ringkasan Terstruktur...
                  </h4>
                  <p className="text-xs text-slate-500 max-w-xs">
                    Menganalisis metodologi, data eksperimen, hasil utama, dan batasan paper secara otomatis.
                  </p>
                </div>
              ) : !summary ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500">
                  <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mb-3 shadow-inner">
                    <svg
                      className="w-7 h-7"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                  </div>
                  <h4 className="text-base font-bold text-slate-800 mb-1">
                    Ringkasan Belum Dibuat
                  </h4>
                  <p className="text-xs text-slate-500 max-w-sm mb-6 leading-relaxed">
                    Dapatkan gambaran menyeluruh paper ini dalam hitungan detik: pertanyaan riset, arsitektur metode, dataset, hasil pengujian, dan keterbatasannya.
                  </p>
                  <button
                    type="button"
                    onClick={() => handleGenerateSummary(false)}
                    disabled={isGeneratingSummary}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm hover:shadow transition disabled:opacity-50"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                      />
                    </svg>
                    <span>Ekstrak Ringkasan Sekarang</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-4 pb-6">
                  {/* Banner TL;DR */}
                  {summary.content.tldr && (
                    <div className="p-4 rounded-xl bg-gradient-to-br from-blue-500/10 via-indigo-500/5 to-slate-50 border border-blue-200/80 shadow-xs">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-xs font-bold text-blue-700 uppercase tracking-wider flex items-center gap-1.5">
                          <span>⚡</span> Intisari Paper (TL;DR)
                        </span>
                      </div>
                      <p className="text-xs font-medium text-slate-800 leading-relaxed">
                        {summary.content.tldr}
                      </p>
                    </div>
                  )}

                  {/* 6 Kartu Aspek Ilmiah Terstruktur */}
                  <div className="space-y-3">
                    {/* 1. Pertanyaan Penelitian */}
                    <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs hover:border-slate-300 transition">
                      <div className="flex items-center gap-2 mb-1 text-slate-800 font-semibold text-xs">
                        <span className="text-sm">🎯</span>
                        <span>Pertanyaan Penelitian</span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {summary.content.research_question}
                      </p>
                    </div>

                    {/* 2. Metodologi */}
                    <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs hover:border-slate-300 transition">
                      <div className="flex items-center gap-2 mb-1 text-slate-800 font-semibold text-xs">
                        <span className="text-sm">⚙️</span>
                        <span>Metodologi & Arsitektur</span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {summary.content.method}
                      </p>
                    </div>

                    {/* 3. Dataset */}
                    <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs hover:border-slate-300 transition">
                      <div className="flex items-center gap-2 mb-1 text-slate-800 font-semibold text-xs">
                        <span className="text-sm">📊</span>
                        <span>Dataset & Sampel Data</span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {summary.content.dataset}
                      </p>
                    </div>

                    {/* 4. Metrik Evaluasi */}
                    <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs hover:border-slate-300 transition">
                      <div className="flex items-center gap-2 mb-1 text-slate-800 font-semibold text-xs">
                        <span className="text-sm">📈</span>
                        <span>Metrik Evaluasi</span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {summary.content.metrics}
                      </p>
                    </div>

                    {/* 5. Hasil Utama */}
                    <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs hover:border-slate-300 transition">
                      <div className="flex items-center gap-2 mb-1 text-slate-800 font-semibold text-xs">
                        <span className="text-sm">🏆</span>
                        <span>Hasil Utama & Temuan</span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {summary.content.results}
                      </p>
                    </div>

                    {/* 6. Keterbatasan */}
                    <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs hover:border-slate-300 transition">
                      <div className="flex items-center gap-2 mb-1 text-slate-800 font-semibold text-xs">
                        <span className="text-sm">⚠️</span>
                        <span>Keterbatasan & Batasan Studi</span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {summary.content.limitations}
                      </p>
                    </div>
                  </div>

                  {/* Pintasan Aksi Tanya Lanjutan di Chat */}
                  <div className="pt-2">
                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Lanjutkan Diskusi di Tanya Jawab:
                    </div>
                    <div className="grid grid-cols-1 gap-1.5">
                      <button
                        type="button"
                        onClick={() => {
                          setActiveTab("chat");
                          handleSendMessage(
                            "Bisa jelaskan lebih detail tentang metodologi yang digunakan di paper ini?"
                          );
                        }}
                        className="text-left p-2.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-700 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 transition"
                      >
                        💬 &ldquo;Bisa jelaskan lebih detail tentang metodologi di paper ini?&rdquo;
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setActiveTab("chat");
                          handleSendMessage(
                            "Bagaimana analisis perbandingan hasil eksperimen paper ini dengan model lain?"
                          );
                        }}
                        className="text-left p-2.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-700 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 transition"
                      >
                        💬 &ldquo;Bagaimana analisis perbandingan hasil eksperimen dengan model lain?&rdquo;
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <>
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
        </>
      )}
    </section>
      </main>

      {/* Floating Action Button untuk Seleksi Istilah */}
      {tooltipPosition && (
        <div
          style={{
            position: "fixed",
            left: `${tooltipPosition.x}px`,
            top: `${tooltipPosition.y}px`,
            transform: "translate(-50%, -100%)",
            zIndex: 50,
          }}
          className="animate-in fade-in zoom-in-95 duration-150"
        >
          <button
            type="button"
            onMouseDown={(e) => {
              // Mencegah blur / deselect saat tombol diklik
              e.preventDefault();
            }}
            onClick={handleExplainTerm}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white text-xs font-semibold rounded-full shadow-lg hover:bg-blue-600 transition cursor-pointer"
          >
            <span>💡</span>
            <span>Jelaskan Istilah</span>
          </button>
        </div>
      )}

      {/* Popover / Modal Penjelasan Istilah */}
      {showExplainModal && (
        <div className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full overflow-hidden p-5 animate-in zoom-in-95 duration-200">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-blue-50 text-blue-600 text-base">
                  💡
                </span>
                <div>
                  <h4 className="text-sm font-bold text-slate-900 leading-tight">
                    {explainedData?.term || selectedTerm}
                  </h4>
                  <span className="text-[10px] text-slate-400">
                    Penjelasan Konsep Ilmiah
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowExplainModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            {isExplainingTerm ? (
              <div className="py-8 flex flex-col items-center justify-center gap-2.5 text-center">
                <svg
                  className="animate-spin h-6 w-6 text-blue-600"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8H4z"
                  ></path>
                </svg>
                <span className="text-xs text-slate-500 font-medium">
                  Menyusun penjelasan singkat dari model...
                </span>
              </div>
            ) : explainedData ? (
              <div className="space-y-3">
                <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-100">
                  {explainedData.explanation}
                </p>

                {explainedData.context && (
                  <div className="p-2.5 rounded-lg bg-slate-100/70 border border-slate-200/60 text-[11px] text-slate-500 italic">
                    <span className="font-semibold text-slate-600 not-italic mr-1">
                      Konteks:
                    </span>
                    &ldquo;{explainedData.context}&rdquo;
                  </div>
                )}

                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setShowExplainModal(false);
                      setActiveTab("chat");
                      handleSendMessage(
                        `Bisa jelaskan lebih dalam mengenai konsep "${explainedData.term}" dan bagaimana penerapannya pada paper ini?`
                      );
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-lg transition shadow-xs cursor-pointer"
                  >
                    <span>💬 Tanya Lanjutan di Chat</span>
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
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
