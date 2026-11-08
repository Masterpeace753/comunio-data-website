import { apiFetch } from "./client";
import type { IngestRunsResponse } from "./types";

export const getIngestRuns = ({ limit = 25, offset = 0 }: { limit?: number; offset?: number } = {}) =>
  apiFetch<IngestRunsResponse>(`/api/v1/ingest/runs?${new URLSearchParams({ limit: String(limit), offset: String(offset) })}`);
