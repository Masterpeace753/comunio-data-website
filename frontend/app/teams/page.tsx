"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getTeams } from "@/lib/api/teams";
import type { Page, TeamSummary } from "@/lib/api/types";
import { TeamTable } from "@/components/tables/DataTables";
import { EmptyState, ErrorState, Skeleton } from "@/components/shared/States";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
export default function TeamsPage() { const [data, setData] = useState<Page<TeamSummary>>(); const [search, setSearch] = useState(""); const [submitted, setSubmitted] = useState(""); const [error, setError] = useState(false); useEffect(() => { getTeams({ limit: 25, search: submitted || undefined }).then(setData).catch(() => setError(true)); }, [submitted]); if (error) return <ErrorState/>; return <><PageHeader eyebrow="Liga-Struktur" title="Teams" description="Kaderstärken und Ligazugehörigkeiten im aktuellen Datenbestand." action={<Link className="button" href="/teams">Filter zurücksetzen</Link>}/><form className="mb-5 flex max-w-xl gap-2" onSubmit={(event) => { event.preventDefault(); setSubmitted(search); }}><input className="input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Team suchen..."/><button className="button bg-accent text-white" type="submit">Suchen</button></form><div className="panel">{!data ? <div className="space-y-4 p-6"><Skeleton className="h-8"/><Skeleton className="h-8"/><Skeleton className="h-8"/></div> : data.items.length ? <><TeamTable items={data.items}/><Pagination {...data} base="/teams"/></> : <EmptyState title="Keine Teams gefunden" text="Passe deine Suche an."/>}</div></>; }
