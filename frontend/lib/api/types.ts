export type Position = "TW" | "ABW" | "MITT" | "ST";
export type Page<T> = { items: T[]; limit: number; offset: number; total: number };
export type PlayerSummary = { id: number; comunio_player_id: number; name: string; position: Position; team_id: number | null; team_name: string | null; current_value_eur: number | null };
export type PlayerDetail = PlayerSummary & { source: string; first_seen_at: string; last_seen_at: string; updated_at: string };
export type TeamSummary = { id: number; comunio_team_id: number; name: string; league: string | null; season: string | null; player_count: number };
export type TeamDetail = TeamSummary & { updated_at: string };
export type MarketValuePoint = { snapshot_date: string; captured_at: string; value_eur: number; previous_snapshot_date: string | null; previous_value_eur: number | null; delta_previous_day_eur: number | null; first_snapshot_date: string | null; first_value_eur: number | null; delta_first_eur: number | null; percent_delta_previous_day: number | null; percent_delta_first: number | null };
export type PlayerHistoryResponse = { player_id: number; from_date: string | null; to_date: string | null; items: MarketValuePoint[] };
export type TransferMarketItem = { player_id: number; player_name: string; position: Position; team_id: number | null; team_name: string | null; snapshot_date: string; listed: boolean; price_eur: number | null; owner_name: string | null };
export type TransferMarketResponse = { items: TransferMarketItem[]; snapshot_date: string | null; limit: number; offset: number; total: number };
export type IngestRunType = "manual" | "scheduled" | "unknown";
export type IngestRunStatus = "started" | "success" | "failed" | "unknown";
export type IngestStage = "login" | "snapshot" | "persistence";
export type IngestErrorCode =
  | "authentication_failed"
  | "snapshot_fetch_failed"
  | "database_persistence_failed"
  | "unexpected_error";
export type IngestRun = {
  id: number | string;
  run_type: IngestRunType;
  status: IngestRunStatus;
  started_at: string;
  finished_at: string | null;
  records_written: number;
  stage: IngestStage | null;
  error_code: IngestErrorCode | null;
};
export type IngestRunsResponse = {
  current_data_date: string | null;
  items: IngestRun[];
  limit: number;
  offset: number;
  total: number;
};