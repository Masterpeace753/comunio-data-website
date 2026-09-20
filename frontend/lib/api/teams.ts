import { apiFetch } from "./client";
import type { Page, TeamDetail, TeamSummary } from "./types";
export const getTeams = (params: { limit?: number; offset?: number; search?: string; league?: string; season?: string } = {}) => apiFetch<Page<TeamSummary>>(`/api/v1/teams?${new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== "") as [string, string][]).toString()}`);
export const getTeam = (id: string) => apiFetch<TeamDetail>(`/api/v1/teams/${id}`);