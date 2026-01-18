"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";

import { DataTable } from "@/components/data-table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type PositionRow = {
  id: number;
  strategy_id: string;
  strategy_name: string;
  symbol: string;
  side: string;
  qty: number;
  avg_entry_price: number;
  current_price: number | null;
  unrealized_pl_usd: number | null;
  unrealized_pl_pct: number | null;
  realized_pl_usd: number | null;
  open_time: string;
  last_sync_time: string | null;
  status: string;
};

export default function DashboardPage() {
  const [positions, setPositions] = useState<PositionRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/positions", { cache: "no-store" });
        const json = await res.json();
        if (!cancelled) setPositions(Array.isArray(json) ? json : []);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const columns = useMemo<ColumnDef<PositionRow>[]>(
    () => [
      { accessorKey: "strategy_name", header: "Strategy" },
      { accessorKey: "symbol", header: "Symbol" },
      { accessorKey: "side", header: "Side" },
      { accessorKey: "qty", header: "Qty" },
      { accessorKey: "avg_entry_price", header: "Avg Entry" },
      { accessorKey: "current_price", header: "Current Price" },
      { accessorKey: "unrealized_pl_usd", header: "Unrealized P&L $" },
      { accessorKey: "unrealized_pl_pct", header: "Unrealized P&L %" },
      { accessorKey: "realized_pl_usd", header: "Realized P&L $" },
      { accessorKey: "open_time", header: "Entry Time" },
      { accessorKey: "last_sync_time", header: "Last Sync" },
      { accessorKey: "status", header: "Status" }
    ],
    []
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-600">Open positions across strategies (separate rows per strategy).</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
          <CardDescription>
            Note: current price / P&amp;L will populate once Alpaca sync is implemented.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? <div className="text-sm text-slate-600">Loading…</div> : <DataTable data={positions} columns={columns} />}
        </CardContent>
      </Card>
    </div>
  );
}

