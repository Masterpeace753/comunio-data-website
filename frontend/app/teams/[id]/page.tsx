"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { getTeam } from "@/lib/api/teams";
import { getPlayers } from "@/lib/api/players";
import type { PlayerSummary, TeamDetail } from "@/lib/api/types";
import { PlayerTable } from "@/components/tables/DataTables";
import { ErrorState, Skeleton } from "@/components/shared/States";
export default function TeamDetailPage({ params }: { params: { id: string } }) { const [team, setTeam] = useState<TeamDetail>(); const [players, setPlayers] = useState<PlayerSummary[]>([]); const [error, setError] = useState(false); useEffect(() => { Promise.all([getTeam(params.id), getPlayers({ team_id: params.id, limit: 100 })]).then(([t, p]) => { setTeam(t); setPlayers(p.items); }).catch(() => setError(true)); }, [params.id]); if (error) return <ErrorState text="Dieses Team wurde nicht gefunden oder die API ist nicht erreichbar."/>; if (!team) return <><Skeleton className="h-10 w-64"/><Skeleton className="mt-8 h-96 w-full"/></>; return <><Link href="/teams" className="mb-8 inline-flex items-center gap-2 text-sm text-secondary hover:text-accent"><ArrowLeft size={16}/> Zur Teamliste</Link><p className="eyebrow">Teamprofil · {team.league ?? "Liga unbekannt"}</p><h1 className="mt-2 text-4xl font-bold">{team.name}</h1><div className="mt-3 flex gap-4 text-sm text-secondary"><span>{team.season ?? "Saison unbekannt"}</span><span>{team.player_count} Spieler</span></div><div className="panel mt-8 p-1"><PlayerTable items={players}/></div></>; }