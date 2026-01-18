"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";

import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type TradeRow = {
  trade_id: string;
  strategy_id: string;
  strategy_name: string;
  symbol: string;
  side: string;
  event: string | null;
  signal_time: string | null;
  signal_price: number | string | null;
  order: {
    status: string | null;
    qty: number | null;
    notional: number | null;
    alpaca_order_id: string | null;
    submitted_at: string | null;
    filled_at: string | null;
    filled_avg_price: number | null;
    filled_qty: number | null;
  } | null;
};

export default function StrategyDetailPage({ params }: { params: { strategyId: string } }) {
  const strategyId = params.strategyId;

  const [trades, setTrades] = useState<TradeRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/trades?strategy_id=${encodeURIComponent(strategyId)}`, { cache: "no-store" });
        const json = await res.json();
        if (!cancelled) setTrades(Array.isArray(json) ? json : []);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [strategyId]);

  const columns = useMemo<ColumnDef<TradeRow>[]>(
    () => [
      { accessorKey: "trade_id", header: "Trade ID" },
      { accessorKey: "symbol", header: "Symbol" },
      { accessorKey: "event", header: "Event" },
      { accessorKey: "side", header: "Side" },
      { accessorKey: "signal_time", header: "Signal Time" },
      { accessorKey: "signal_price", header: "Signal Price" },
      {
        id: "qty_or_notional",
        header: "Qty/Notional",
        cell: ({ row }) => {
          const o = row.original.order;
          if (!o) return "-";
          if (o.qty != null) return `qty ${o.qty}`;
          if (o.notional != null) return `$${o.notional}`;
          return "-";
        }
      },
      {
        id: "order_status",
        header: "Order Status",
        cell: ({ row }) => row.original.order?.status ?? "-"
      },
      {
        id: "fill",
        header: "Fill",
        cell: ({ row }) => {
          const o = row.original.order;
          if (!o) return "-";
          if (o.filled_qty != null && o.filled_avg_price != null) return `${o.filled_qty} @ ${o.filled_avg_price}`;
          return "-";
        }
      }
    ],
    []
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Strategy</h1>
          <p className="mt-1 text-sm text-slate-600">
            {strategyId} — Trades are paired by <code>trade_id</code> (signals + Alpaca order status).
          </p>
        </div>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Trades</CardTitle>
          <CardDescription>
            Shows TradingView signal time/price + Alpaca order status. Timestamps are simplified; JSON payload is hidden.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-sm text-slate-600">Loading…</div>
          ) : (
            <DataTable data={trades} columns={columns} searchPlaceholder="Search trades…" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

