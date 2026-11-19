const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "telaah_token";

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Paper {
  id: string;
  user_id: string;
  title: string | null;
  authors: string[] | null;
  source_type: string | null;
  source_ref: string | null;
  file_path: string;
  status: "uploaded" | "parsing" | "embedding" | "ready" | "failed" | string;
  error_message: string | null;
  page_count: number | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${API_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `HTTP error ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (typeof errorData.detail === "string") {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail
            .map((err: { msg: string }) => err.msg)
            .join(", ");
        }
      }
    } catch {
      // response wasn't JSON
    }
    throw new Error(errorMessage);
  }

  // Handle 204 No Content or responses without a body
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined as unknown as T;
  }

  return response.json();
}

export async function registerUser(
  email: string,
  password: string
): Promise<User> {
  return apiFetch<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function loginUser(
  email: string,
  password: string
): Promise<TokenResponse> {
  const data = await apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setStoredToken(data.access_token);
  return data;
}

export async function getCurrentUser(): Promise<User> {
  return apiFetch<User>("/auth/me");
}

export function logoutUser(): void {
  setStoredToken(null);
}

export async function getPapers(): Promise<Paper[]> {
  return apiFetch<Paper[]>("/papers");
}

export async function getPaper(id: string): Promise<Paper> {
  return apiFetch<Paper>(`/papers/${id}`);
}

export async function uploadPaper(file: File): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch<Paper>("/papers", {
    method: "POST",
    body: formData,
  });
}

export async function importFromArxiv(arxivUrl: string): Promise<Paper> {
  return apiFetch<Paper>("/papers/arxiv", {
    method: "POST",
    body: JSON.stringify({ arxiv_url: arxivUrl }),
  });
}

export async function deletePaper(id: string): Promise<void> {
  await apiFetch<void>(`/papers/${id}`, {
    method: "DELETE",
  });
}

export interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Citation {
  citation_number: number;
  chunk_id: string;
  section: string | null;
  page_start: number | null;
  page_end: number | null;
  bbox: BoundingBox | null;
  snippet: string;
  verified: boolean;
}

export interface RetrievedContextChunk {
  index: number;
  chunk_id: string;
  section: string | null;
  page_start: number | null;
  page_end: number | null;
  text: string;
  bbox: BoundingBox | null;
  similarity_score?: number;
}

export interface ConversationItem {
  id: string;
  paper_id: string;
  user_id: string;
  created_at: string;
  message_count: number;
  preview: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  not_found?: boolean;
  context_chunks?: RetrievedContextChunk[];
  created_at?: string;
}

export async function getPaperConversations(
  paperId: string
): Promise<ConversationItem[]> {
  return apiFetch<ConversationItem[]>(`/papers/${paperId}/chat/conversations`);
}

export async function getConversationMessages(
  paperId: string,
  conversationId: string
): Promise<ChatMessage[]> {
  const rawList = await apiFetch<
    Array<{
      id: string;
      conversation_id: string;
      role: "user" | "assistant";
      content: string;
      citations?: Citation[];
      created_at: string;
    }>
  >(`/papers/${paperId}/chat/conversations/${conversationId}/messages`);

  return rawList.map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    citations: m.citations,
    created_at: m.created_at,
  }));
}

export async function deleteConversation(
  paperId: string,
  conversationId: string
): Promise<void> {
  return apiFetch<void>(
    `/papers/${paperId}/chat/conversations/${conversationId}`,
    {
      method: "DELETE",
    }
  );
}

export async function streamPaperChat(
  paperId: string,
  message: string,
  callbacks: {
    onContext?: (chunks: RetrievedContextChunk[]) => void;
    onDelta?: (token: string) => void;
    onDone?: (data: {
      message_id: string;
      conversation_id?: string;
      citations: Citation[];
      not_found?: boolean;
    }) => void;
    onError?: (err: string) => void;
  },
  signal?: AbortSignal,
  conversationId?: string | null
): Promise<void> {
  const token = getStoredToken();
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${API_URL}/papers/${paperId}/chat`;
  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      message,
      conversation_id: conversationId || undefined,
    }),
    signal,
  });

  if (!response.ok) {
    let errorMsg = `HTTP error ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) errorMsg = errJson.detail;
    } catch {
      // not JSON
    }
    throw new Error(errorMsg);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Respons server tidak mendukung ReadableStream");
  }

  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const evtBlock of events) {
      if (!evtBlock.trim()) continue;

      let eventType = "message";
      let dataStr = "";

      const lines = evtBlock.split("\n");
      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventType = line.replace("event:", "").trim();
        } else if (line.startsWith("data:")) {
          dataStr = line.replace("data:", "").trim();
        }
      }

      if (!dataStr) continue;

      try {
        const parsed = JSON.parse(dataStr);
        if (eventType === "context") {
          callbacks.onContext?.(parsed as RetrievedContextChunk[]);
        } else if (eventType === "delta") {
          if (parsed.delta) {
            callbacks.onDelta?.(parsed.delta);
          }
        } else if (eventType === "done") {
          callbacks.onDone?.(parsed);
        } else if (eventType === "error") {
          callbacks.onError?.(
            parsed.error || "Terjadi kesalahan saat streaming jawaban"
          );
        }
      } catch (err) {
        console.error("Gagal parse SSE JSON data:", err, dataStr);
      }
    }
  }
}

export interface SummaryContent {
  tldr?: string | null;
  research_question: string;
  method: string;
  dataset: string;
  metrics: string;
  results: string;
  limitations: string;
}

export interface SummaryResponse {
  id: string;
  paper_id: string;
  content: SummaryContent;
  prompt_version: string | null;
  created_at: string;
}

export async function getPaperSummary(
  paperId: string
): Promise<SummaryResponse> {
  return apiFetch<SummaryResponse>(`/papers/${paperId}/summary`);
}

export async function generatePaperSummary(
  paperId: string
): Promise<SummaryResponse> {
  return apiFetch<SummaryResponse>(`/papers/${paperId}/summary`, {
    method: "POST",
  });
}

export async function regeneratePaperSummary(
  paperId: string
): Promise<SummaryResponse> {
  return apiFetch<SummaryResponse>(`/papers/${paperId}/summary/regenerate`, {
    method: "POST",
  });
}




