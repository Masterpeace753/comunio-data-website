"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { getPlayers } from "@/lib/api/players";
import type { Page, PlayerSummary } from "@/lib/api/types";
import { PlayerTable } from "@/components/tables/DataTables";
import { EmptyState, ErrorState, Skeleton } from "@/components/shared/States";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";

const PAGE_SIZE = 25;

function LoadingPlayers() {
  return <div className="space-y-4 p-6"><Skeleton className="h-8"/><Skeleton className="h-8"/><Skeleton className="h-8"/></div>;
}

function PlayersList({ submitted, offset }: { submitted: string; offset: number }) {
  const router = useRouter();
  const [search, setSearch] = useState(submitted);
  const [result, setResult] = useState<{
    offset: number;
    data?: Page<PlayerSummary>;
    error?: boolean;
  }>();

  useEffect(() => {
    let active = true;
    getPlayers({ limit: PAGE_SIZE, offset, search: submitted || undefined })
      .then((data) => {
        if (active) setResult({ offset, data });
      })
      .catch(() => {
        if (active) setResult({ offset, error: true });
      });
    return () => { active = false; };
  }, [offset, submitted]);

  const current = result?.offset === offset ? result : undefined;
  if (current?.error) return <ErrorState/>;
  const data = current?.data;
  const query = new URLSearchParams(submitted ? { search: submitted } : {}).toString();

  return (
    <>
      <PageHeader eyebrow="Spieler-Datenbank" title="Spieler" description="Durchsuche Marktwerte und aktuelle Teamzuordnungen aus dem letzten Snapshot." action={<Link className="button" href="/spieler">Filter zurücksetzen</Link>}/>
      <form className="mb-5 flex max-w-xl gap-2" onSubmit={(event) => {
        event.preventDefault();
        const params = new URLSearchParams();
        if (search.trim()) params.set("search", search.trim());
        const queryString = params.toString();
        router.push(queryString ? `/spieler?${queryString}` : "/spieler");
      }}>
        <input className="input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Spieler suchen..." maxLength={100}/>
        <button className="button bg-accent text-white" type="submit">Suchen</button>
      </form>
      <div className="panel">
        {!data ? <LoadingPlayers/> : (
          <>
            {data.items.length ? <PlayerTable items={data.items}/> : <EmptyState title="Keine Spieler gefunden" text="Passe deine Suche an oder warte auf den nächsten Snapshot."/>}
            {(data.items.length > 0 || data.offset > 0) && <Pagination {...data} base="/spieler" query={query}/>}
          </>
        )}
      </div>
    </>
  );
}

function PlayersPageContent() {
  const params = useSearchParams();
  const submitted = params.get("search") ?? "";
  const rawOffset = params.get("offset") ?? "0";
  const parsedOffset = Number(rawOffset);
  const offset = /^\d+$/.test(rawOffset) && Number.isSafeInteger(parsedOffset) ? parsedOffset : 0;
  return <PlayersList key={submitted} submitted={submitted} offset={offset}/>;
}

export default function PlayersPage() {
  return <Suspense fallback={<LoadingPlayers/>}><PlayersPageContent/></Suspense>;
}
