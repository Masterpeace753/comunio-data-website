export class ApiError extends Error { constructor(public status: number, public code: string, message: string) { super(message); } }
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, { ...init, headers: { Accept: "application/json", ...init?.headers }, credentials: "omit" });
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new ApiError(response.status, body.code ?? "api_error", response.status === 503 ? "Daten aktuell nicht verfuegbar." : response.status === 404 ? "Ressource nicht gefunden." : "Die Daten konnten nicht geladen werden."); }
  return response.json() as Promise<T>;
}