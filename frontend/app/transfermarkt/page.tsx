"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getTransfermarket } from "@/lib/api/transfermarket";
import type { TransferMarketResponse } from "@/lib/api/types";
import { TransferTable } from "@/components/tables/DataTables";
import { EmptyState, ErrorState, Skeleton } from "@/components/shared/States";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { dateLabel } from "@/lib/format";
export default function TransfermarketPage() { const [data, setData] = useState<TransferMarketResponse>(); const [error, setError] = useState(false); useEffect(() => { getTransfermarket({ limit: 25 }).then(setData).catch(() => setError(true)); }, []); if (error) return <ErrorState/>; const showOwner = process.env.NEXT_PUBLIC_SHOW_OWNER_NAME !== "false"; return <><PageHeader eyebrow="Marktplatz" title="Transfermarkt" description="Aktuelle Angebote aus dem letzten verfügbaren Snapshot." action={<Link className="button" href="/transfermarkt">Aktualisieren</Link>}/>{data?.snapshot_date && <div className="mb-5 flex items-center justify-between rounded-xl border border-accent/30 bg-accent/10 px-4 py-3 text-sm"><span className="text-secondary">Snapshot</span><strong>{dateLabel(data.snapshot_date)}</strong></div>}{!data ? <Skeleton className="h-96"/> : data.items.length ? <div className="panel"><TransferTable items={data.items} showOwner={showOwner}/><Pagination {...data} base="/transfermarkt"/></div> : <EmptyState title="Transfermarktdaten werden aktuell noch nicht befuellt." text="Die Ingest-Pipeline liefert für diesen Bereich derzeit noch keine Einträge."/>}</>; }
