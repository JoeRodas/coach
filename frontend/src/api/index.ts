// Picks the real or mock API at module load time.
//
// Convention: the mock is used when VITE_API_BASE_URL is unset. That covers
// (a) local dev with no backend running, (b) the staging Pages deploy at
// coach-frontend.pages.dev / chesscoach-v2.nuezmiami.com until §6.4 ships
// a real backend. Once that backend exists, set VITE_API_BASE_URL in the
// Pages env vars and the SPA flips to real calls with no code change.

import { api as realApi } from "./client";
import { mockApi } from "./mock";

const useMock = !import.meta.env.VITE_API_BASE_URL;

export const api = useMock ? mockApi : realApi;
export const isMockApi = useMock;
