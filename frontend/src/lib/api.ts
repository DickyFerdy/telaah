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



