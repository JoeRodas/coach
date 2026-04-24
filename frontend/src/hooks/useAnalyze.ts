// react-query useMutation wrapper around api.analyze. Exposes the same
// {mutate, data, error, isPending, reset} surface the components need
// without leaking react-query types upward.

import { useMutation } from "@tanstack/react-query";
import { api } from "../api";
import type { AnalysisRequest, AnalysisResponse } from "../types/api";

export function useAnalyze() {
  return useMutation<AnalysisResponse, Error, AnalysisRequest>({
    mutationFn: (req) => api.analyze(req),
  });
}
