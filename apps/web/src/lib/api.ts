/**
 * 前端 API 调用工具
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new ApiError(error.error?.message || error.detail || `API 錯誤: ${res.status}`, res.status);
  }

  return res.json();
}

/**
 * 文件上传 - 使用 FormData，不设置 Content-Type 让浏览器自动处理
 */
export async function apiUpload<T>(
  path: string,
  file: File,
  extraFields?: Record<string, string>
): Promise<T> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);

  if (extraFields) {
    for (const [key, value] of Object.entries(extraFields)) {
      formData.append(key, value);
    }
  }

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new ApiError(error.error?.message || error.detail || `上傳失敗: ${res.status}`, res.status);
  }

  return res.json();
}

/**
 * 获取文件访问 URL
 */
export function getFileUrl(fileId: string): string {
  return `${API_BASE}/files/${fileId}/content`;
}

// ===== Token 管理 =====

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function setToken(token: string): void {
  localStorage.setItem("access_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_info");
}

export function getUserInfo(): { id: string; username: string; roles: string[]; full_name?: string } | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("user_info");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setUserInfo(user: { id: string; username: string; roles: string[]; full_name?: string }): void {
  localStorage.setItem("user_info", JSON.stringify(user));
}

export function getUserRole(): string | null {
  const user = getUserInfo();
  return user?.roles?.[0] || null;
}

export function isLoggedIn(): boolean {
  return !!getToken();
}
