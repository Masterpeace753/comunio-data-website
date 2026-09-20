"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getPlayers } from "@/lib/api/players";
import type { Page, PlayerSummary } from "@/lib/api/types";
import { PlayerTable } from "@/components/tables/DataTables";
import { EmptyState, ErrorState, Skeleton } from "@/components/shared/States";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
export default function PlayersPage() { const [data, setData] = useState<Page<PlayerSummary>>(); const [search, setSearch] = useState(""); const [submitted, setSubmitted] = useState(""); const [error, setError] = useState(false); useEffect(() => { getPlayers({ limit: 25, search: submitted || undefined }).then(setData).catch(() => setError(true)); }, [submitted]); if (error) return <ErrorState/>; return <><PageHeader eyebrow="Spieler-Datenbank" title="Spieler" description="Durchsuche Marktwerte und aktuelle Teamzuordnungen aus dem letzten Snapshot." action={<Link className="button" href="/spieler">Filter zurücksetzen</Link>}/><form className="mb-5 flex max-w-xl gap-2" onSubmit={(event) => { event.preventDefault(); setSubmitted(search); }}><input className="input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Spieler suchen..."/><button className="button bg-accent text-white" type="submit">Suchen</button></form><div className="panel">{!data ? <div className="space-y-4 p-6"><Skeleton className="h-8"/><Skeleton className="h-8"/><Skeleton className="h-8"/></div> : data.items.length ? <><PlayerTable items={data.items}/><Pagination {...data} base="/spieler"/></> : <EmptyState title="Keine Spieler gefunden" text="Passe deine Suche an oder warte auf den nächsten Snapshot."/>}</div></>; }
