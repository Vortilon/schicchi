"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";

import { DataTable } from "@/components/data-table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type StrategyRow = {
  id: string;
  name: string;
  is_active: boolean;
  open_positions_count: number;
  pnl_usd: number;
  pnl_pct: number;
  buy_hold_basis_usd: number | null;
  buy_hold_usd: number | null;
  buy_hold_pct: number | null;
  notes?: string;
};

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<StrategyRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/strategies", { cache: "no-store" });
        const json = await res.json();
        if (!cancelled) setStrategies(Array.isArray(json) ? json : []);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const columns = useMemo<ColumnDef<StrategyRow>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Strategy",
        cell: ({ row }) => (
          <a className="text-slate-900 underline underline-offset-4" href={`/strategies/${row.original.id}`}>
            {row.original.name}
          </a>
        )
      },
      { accessorKey: "is_active", header: "Active" },
      { accessorKey: "open_positions_count", header: "Open Positions" },
      { accessorKey: "pnl_pct", header: "P&L %" },
      { accessorKey: "pnl_usd", header: "P&L $" },
      { accessorKey: "buy_hold_pct", header: "Buy & Hold %" },
      { accessorKey: "buy_hold_usd", header: "Buy & Hold $" }
    ],
    []
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Strategies</h1>
        <p className="mt-1 text-sm text-slate-600">
          Active strategies, open position counts, and baseline buy-and-hold comparison.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Strategy Summary</CardTitle>
          <CardDescription>
            Buy &amp; Hold USD uses the same initial notional as the strategy’s sizing (default $1000) for a fair $ comparison.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-sm text-slate-600">Loading…</div>
          ) : (
            <DataTable data={strategies} columns={columns} searchPlaceholder="Search strategies…" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

