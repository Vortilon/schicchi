"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";

import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
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

type Account = {
  cash: number;
  equity: number;
  buying_power: number;
  portfolio_value: number;
};

type TxRow = {
  trade_id: string;
  strategy_name: string;
  symbol: string;
  event: string;
  side: string;
  signal_time: string;
  signal_price: number | string | null;
  alpaca_status: string | null;
  alpaca_error: string | null;
  filled_qty: number | null;
  filled_avg_price: number | null;
};

export default function DashboardPage() {
  const [positions, setPositions] = useState<PositionRow[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [tx, setTx] = useState<TxRow[]>([]);
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  async function loadAll() {
    const [posRes, stratRes, txRes, acctRes] = await Promise.all([
      fetch("/api/positions", { cache: "no-store" }),
      fetch("/api/strategies?active_only=true", { cache: "no-store" }),
      fetch("/api/transactions?today_only=true&limit=200", { cache: "no-store" }),
      fetch("/api/alpaca/account", { cache: "no-store" })
    ]);

    const posJson = await posRes.json();
    const stratJson = await stratRes.json();
    const txJson = await txRes.json();
    const acctJson = await acctRes.json();

    setPositions(Array.isArray(posJson) ? posJson : []);
    setStrategies(Array.isArray(stratJson) ? stratJson : []);
    setTx(Array.isArray(txJson) ? txJson : []);
    setAccount(acctJson?.cash != null ? acctJson : null);
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadAll();
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

  const txColumns = useMemo<ColumnDef<TxRow>[]>(
    () => [
      { accessorKey: "signal_time", header: "Time" },
      { accessorKey: "strategy_name", header: "Strategy" },
      { accessorKey: "symbol", header: "Symbol" },
      { accessorKey: "event", header: "Event" },
      { accessorKey: "side", header: "Side" },
      { accessorKey: "signal_price", header: "Signal Price" },
      { accessorKey: "alpaca_status", header: "Alpaca Status" },
      {
        id: "fill",
        header: "Fill",
        cell: ({ row }) => {
          const r = row.original;
          if (r.filled_qty != null && r.filled_avg_price != null) return `${r.filled_qty} @ ${r.filled_avg_price}`;
          return "-";
        }
      },
      { accessorKey: "alpaca_error", header: "Error" }
    ],
    []
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600">
            Today’s overview: account balance, open positions, strategies performance summary, and last activity.
          </p>
        </div>
        <Button
          variant="outline"
          disabled={syncing}
          onClick={async () => {
            setSyncing(true);
            try {
              await fetch("/api/sync/alpaca", { method: "POST" });
              await loadAll();
            } finally {
              setSyncing(false);
            }
          }}
        >
          {syncing ? "Refreshing…" : "Refresh (sync Alpaca)"}
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Cash</CardTitle>
            <CardDescription>Alpaca account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{account ? `$${account.cash.toFixed(2)}` : "-"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Equity</CardTitle>
            <CardDescription>Alpaca account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{account ? `$${account.equity.toFixed(2)}` : "-"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Buying Power</CardTitle>
            <CardDescription>Alpaca account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{account ? `$${account.buying_power.toFixed(2)}` : "-"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Open Positions</CardTitle>
            <CardDescription>rows</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{positions.length}</div>
          </CardContent>
        </Card>
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

      <Card>
        <CardHeader>
          <CardTitle>Strategies Overview</CardTitle>
          <CardDescription>Active strategies and their current counts (P&amp;L will refine as fills sync matures).</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-sm text-slate-600">Loading…</div>
          ) : (
            <div className="text-sm text-slate-700">
              <ul className="list-disc pl-5">
                {strategies.map((s) => (
                  <li key={s.id}>
                    <a className="underline underline-offset-4" href={`/strategies/${s.id}`}>
                      {s.name}
                    </a>{" "}
                    — open positions: {s.open_positions_count}, P&amp;L: {s.pnl_pct}% (${s.pnl_usd})
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Activity (Today or Last 200)</CardTitle>
          <CardDescription>
            Each TradingView signal row shows the paired Alpaca order status (or error).
          </CardDescription>
        </CardHeader>
        <CardContent>{loading ? <div className="text-sm text-slate-600">Loading…</div> : <DataTable data={tx} columns={txColumns} />}</CardContent>
      </Card>
    </div>
  );
}

