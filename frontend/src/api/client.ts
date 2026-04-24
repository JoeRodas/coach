// Typed fetch wrapper. Every network call in the SPA goes through this — no
// untyped `fetch` anywhere else in the codebase (REQUIREMENTS.md §6.1).
//
// Base URL is relative in dev (Vite proxies /api → :8000) and in production
// (SPA shares origin with FastAPI or is proxied via the Cloudflare Worker).
// Override for staging/preview via VITE_API_BASE_URL.

import type { AnalysisRequest, AnalysisResponse, MetricsSnapshot } from "../types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const ADMIN_SECRET_HEADER = "x-admin-secret";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit & { adminSecret?: string } = {},
): Promise<T> {
  const { adminSecret, headers, ...rest } = init;
  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      "content-type": "application/json",
      ...(adminSecret ? { [ADMIN_SECRET_HEADER]: adminSecret } : {}),
      ...headers,
    },
  });

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(res.status, body, `${res.status} ${res.statusText} on ${path}`);
  }

  return (await res.json()) as T;
}

export const api = {
  analyze: (body: AnalysisRequest) =>
    request<AnalysisResponse>("/api/analyze", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  metrics: (adminSecret: string) => request<MetricsSnapshot>("/api/admin/metrics", { adminSecret }),
};
