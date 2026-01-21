"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";

import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtMoney, fmtNum, fmtPct, fmtTimeEST, numClass } from "@/lib/format";

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
  last_equity?: number | null;
  day_pl_usd?: number | null;
  day_pl_pct?: number | null;
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
  order_type?: string | null;
  limit_price?: number | string | null;
  time_in_force?: string | null;
  alpaca_status: string | null;
  alpaca_error: string | null;
  filled_qty: number | null;
  filled_avg_price: number | null;
};

type AlpacaOrderRow = {
  alpaca_order_id: string;
  client_order_id: string | null;
  strategy_name: string | null;
  symbol: string | null;
  side: string | null;
  order_type: string | null;
  time_in_force: string | null;
  status: string | null;
  qty: number | null;
  notional: number | null;
  limit_price: number | null;
  stop_price: number | null;
  filled_qty: number | null;
  filled_avg_price: number | null;
  submitted_at: string | null;
  filled_at: string | null;
};

export default function DashboardPage() {
  const [positions, setPositions] = useState<PositionRow[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [tx, setTx] = useState<TxRow[]>([]);
  const [orders, setOrders] = useState<AlpacaOrderRow[]>([]);
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [toasts, setToasts] = useState<Array<{ id: string; kind: "info" | "success" | "error"; text: string; tsIso: string }>>([]);
  const [latestTradeId, setLatestTradeId] = useState<string | null>(null);

  async function loadAll() {
    const [posRes, stratRes, txRes, ordersRes, acctRes] = await Promise.all([
      fetch("/api/positions", { cache: "no-store" }),
      fetch("/api/strategies?active_only=true", { cache: "no-store" }),
      fetch("/api/transactions?today_only=true&limit=200", { cache: "no-store" }),
      fetch("/api/alpaca/orders?status=all&limit=200", { cache: "no-store" }),
      fetch("/api/alpaca/account", { cache: "no-store" })
    ]);

    const posJson = await posRes.json();
    const stratJson = await stratRes.json();
    const txJson = await txRes.json();
    const ordersJson = await ordersRes.json();
    const acctJson = await acctRes.json();

    setPositions(Array.isArray(posJson) ? posJson : []);
    setStrategies(Array.isArray(stratJson) ? stratJson : []);
    setTx(Array.isArray(txJson) ? txJson : []);
    setOrders(Array.isArray(ordersJson) ? ordersJson : []);
    const newestRow = Array.isArray(txJson) && txJson.length ? txJson[0] : null;
    const newest = newestRow?.trade_id ?? null;
    if (newest && newest !== latestTradeId) {
      setLatestTradeId(newest);

      const tsIso = newestRow?.signal_time ?? new Date().toISOString();
      const ot = newestRow?.order_type ? ` ${String(newestRow.order_type).toUpperCase()}` : "";
      const base = `${newestRow?.strategy_name ?? "Strategy"}: ${newestRow?.symbol ?? ""} ${newestRow?.event ?? ""} ${newestRow?.side ?? ""}${ot}`.trim();

      // 1) TradingView incoming signal (info)
      const tvMsg = {
        id: `${newest}-tv`,
        kind: "info" as const,
        tsIso,
        text: `TradingView: ${base}`
      };

      // 2) Alpaca result (success/error)
      const alpacaErr = newestRow?.alpaca_error;
      const alpacaStatus = newestRow?.alpaca_status;
      const alpacaMsg =
        alpacaErr != null
          ? {
              id: `${newest}-alpaca-err`,
              kind: "error" as const,
              tsIso,
              text: `Alpaca error: ${newestRow?.symbol ?? ""} ${newestRow?.event ?? ""} — ${alpacaErr}`
            }
          : alpacaStatus
            ? {
                id: `${newest}-alpaca-ok`,
                kind: "success" as const,
                tsIso,
                text: `Alpaca: ${newestRow?.symbol ?? ""} ${newestRow?.event ?? ""} — ${alpacaStatus}`
              }
            : null;

      setToasts((prev) => {
        const next = [tvMsg, ...(alpacaMsg ? [alpacaMsg] : []), ...prev].slice(0, 6);
        return next;
      });

      // auto-expire after 3 seconds
      const expireIds = [tvMsg.id, alpacaMsg?.id].filter(Boolean) as string[];
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => !expireIds.includes(t.id)));
      }, 3000);
    }
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

  // Lightweight “live” indicator: poll activity every 10s and toast on new newest row.
  useEffect(() => {
    const t = setInterval(() => {
      loadAll().catch(() => {});
    }, 10000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestTradeId]);

  const columns = useMemo<ColumnDef<PositionRow>[]>(
    () => [
      { accessorKey: "symbol", header: "Symbol" },
      { accessorKey: "side", header: "Side" },
      {
        accessorKey: "qty",
        header: "Qty",
        cell: ({ row }) => <span className="text-slate-900">{fmtNum(row.original.qty, 2)}</span>
      },
      {
        accessorKey: "avg_entry_price",
        header: "Avg Entry",
        cell: ({ row }) => <span className="text-slate-900">{fmtNum(row.original.avg_entry_price, 2)}</span>
      },
      {
        accessorKey: "current_price",
        header: "Current Price",
        cell: ({ row }) => <span className="text-slate-900">{row.original.current_price == null ? "-" : fmtNum(row.original.current_price, 2)}</span>
      },
      {
        accessorKey: "unrealized_pl_usd",
        header: "Unrealized P&L $",
        cell: ({ row }) => <span className={numClass(row.original.unrealized_pl_usd)}>{fmtMoney(row.original.unrealized_pl_usd)}</span>
      },
      {
        accessorKey: "unrealized_pl_pct",
        header: "Unrealized P&L %",
        cell: ({ row }) => <span className={numClass(row.original.unrealized_pl_pct)}>{fmtPct(row.original.unrealized_pl_pct)}</span>
      },
      {
        accessorKey: "realized_pl_usd",
        header: "Realized P&L $",
        cell: ({ row }) => <span className={numClass(row.original.realized_pl_usd)}>{fmtMoney(row.original.realized_pl_usd)}</span>
      },
      {
        accessorKey: "open_time",
        header: "Entry Time",
        cell: ({ row }) => <span className="text-slate-900">{fmtTimeEST(row.original.open_time)}</span>
      },
      {
        accessorKey: "last_sync_time",
        header: "Last Sync",
        cell: ({ row }) => <span className="text-slate-900">{fmtTimeEST(row.original.last_sync_time)}</span>
      },
      { accessorKey: "status", header: "Status" }
    ],
    []
  );

  const txColumns = useMemo<ColumnDef<TxRow>[]>(
    () => [
      {
        accessorKey: "signal_time",
        header: "Time (EST)",
        cell: ({ row }) => <span className="text-slate-900">{fmtTimeEST(row.original.signal_time)}</span>
      },
      { accessorKey: "strategy_name", header: "Strategy" },
      { accessorKey: "symbol", header: "Symbol" },
      { accessorKey: "event", header: "Event" },
      { accessorKey: "side", header: "Side" },
      {
        accessorKey: "order_type",
        header: "Order Type",
        cell: ({ row }) => (row.original.order_type ? String(row.original.order_type).toUpperCase() : "-")
      },
      {
        accessorKey: "limit_price",
        header: "Limit",
        cell: ({ row }) =>
          row.original.limit_price == null ? "-" : <span className="text-slate-900">{fmtNum(Number(row.original.limit_price), 2)}</span>
      },
      {
        accessorKey: "signal_price",
        header: "Signal Price",
        cell: ({ row }) => {
          const v = row.original.signal_price;
          if (v == null) return "-";
          const n = typeof v === "number" ? v : Number(v);
          return Number.isFinite(n) ? <span className="text-slate-900">{fmtNum(n, 2)}</span> : <span className="text-slate-900">{String(v)}</span>;
        }
      },
      { accessorKey: "alpaca_status", header: "Alpaca Status" },
      {
        id: "fill",
        header: "Fill",
        cell: ({ row }) => {
          const r = row.original;
          if (r.filled_qty != null && r.filled_avg_price != null) return `${fmtNum(r.filled_qty, 2)} @ ${fmtNum(r.filled_avg_price, 2)}`;
          return "-";
        }
      },
      {
        accessorKey: "alpaca_error",
        header: "Error",
        cell: ({ row }) => (row.original.alpaca_error ? <span className="text-red-600">{row.original.alpaca_error}</span> : "-")
      }
    ],
    []
  );

  const ordersColumns = useMemo<ColumnDef<AlpacaOrderRow>[]>(
    () => [
      {
        accessorKey: "submitted_at",
        header: "Submitted (EST)",
        cell: ({ row }) => <span className="text-slate-900">{fmtTimeEST(row.original.submitted_at)}</span>
      },
      { accessorKey: "strategy_name", header: "Strategy" },
      { accessorKey: "symbol", header: "Symbol" },
      { accessorKey: "side", header: "Side" },
      {
        accessorKey: "order_type",
        header: "Type",
        cell: ({ row }) => (row.original.order_type ? String(row.original.order_type).toUpperCase() : "-")
      },
      {
        id: "qty_or_notional",
        header: "Qty/Notional",
        cell: ({ row }) => {
          const r = row.original;
          if (r.qty != null) return <span className="text-slate-900">{fmtNum(r.qty, 2)}</span>;
          if (r.notional != null) return <span className="text-slate-900">{fmtMoney(r.notional)}</span>;
          return "-";
        }
      },
      {
        accessorKey: "limit_price",
        header: "Target/Limit",
        cell: ({ row }) => (row.original.limit_price == null ? "-" : <span className="text-slate-900">{fmtNum(row.original.limit_price, 2)}</span>)
      },
      {
        accessorKey: "filled_avg_price",
        header: "Filled @",
        cell: ({ row }) => (row.original.filled_avg_price == null ? "-" : <span className="text-slate-900">{fmtNum(row.original.filled_avg_price, 2)}</span>)
      },
      {
        accessorKey: "filled_qty",
        header: "Filled Qty",
        cell: ({ row }) => (row.original.filled_qty == null ? "-" : <span className="text-slate-900">{fmtNum(row.original.filled_qty, 2)}</span>)
      },
      { accessorKey: "status", header: "Status" }
    ],
    []
  );

  const stratColumns = useMemo<ColumnDef<any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Strategy",
        cell: ({ row }) => (
          <a className="underline underline-offset-4" href={`/strategies/${row.original.id}`}>
            {row.original.name}
          </a>
        )
      },
      { accessorKey: "open_positions_count", header: "Open Pos" },
      { accessorKey: "symbols_traded", header: "Symbols" },
      { accessorKey: "signals_total", header: "Signals" },
      { accessorKey: "filled_orders_total", header: "Filled Orders" },
      { accessorKey: "trades_total", header: "Round-Trip Trades" },
      { accessorKey: "wins", header: "Wins" },
      { accessorKey: "losses", header: "Losses" },
      {
        id: "pnl_usd",
        header: "P&L $",
        cell: ({ row }) => <span className={numClass(row.original.pnl_usd)}>{fmtMoney(row.original.pnl_usd)}</span>
      },
      {
        id: "pnl_pct",
        header: "P&L %",
        cell: ({ row }) => <span className={numClass(row.original.pnl_pct)}>{fmtPct(row.original.pnl_pct)}</span>
      },
      {
        id: "pf",
        header: "PF",
        cell: ({ row }) => (row.original.profit_factor == null ? "-" : Number(row.original.profit_factor).toFixed(2))
      },
      {
        id: "mdd",
        header: "Max DD",
        cell: ({ row }) => (row.original.max_drawdown_pct == null ? "-" : fmtPct(row.original.max_drawdown_pct))
      },
      {
        id: "bh_pct",
        header: "B&H %",
        cell: ({ row }) =>
          row.original.buy_hold_pct == null ? "-" : <span className={numClass(row.original.buy_hold_pct)}>{fmtPct(row.original.buy_hold_pct)}</span>
      },
      {
        id: "bh_usd",
        header: "B&H $",
        cell: ({ row }) =>
          row.original.buy_hold_usd == null ? "-" : <span className={numClass(row.original.buy_hold_usd)}>{fmtMoney(row.original.buy_hold_usd)}</span>
      }
    ],
    []
  );

  return (
    <div className="space-y-6">
      {toasts.length ? (
        <div className="fixed right-6 top-20 z-50 space-y-2">
          {toasts.map((t) => (
            <div
              key={t.id}
              className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm shadow-lg"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="text-xs text-slate-500">{fmtTimeEST(t.tsIso)}</div>
                <div
                  className={
                    t.kind === "success"
                      ? "text-emerald-700"
                      : t.kind === "error"
                        ? "text-red-600"
                        : "text-blue-700"
                  }
                >
                  {t.kind === "success" ? "Success" : t.kind === "error" ? "Error" : "Info"}
                </div>
              </div>
              <div className="mt-1 text-slate-900">{t.text}</div>
            </div>
          ))}
        </div>
      ) : null}
      <div className="flex items-start justify-between gap-4">
        <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
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

      <div className="grid gap-4 md:grid-cols-6">
        <Card>
          <CardHeader>
            <CardTitle>Cash</CardTitle>
            <CardDescription>Alpaca account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{account ? fmtMoney(account.cash) : "-"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Equity</CardTitle>
            <CardDescription>Alpaca account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{account ? fmtMoney(account.equity) : "-"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Day P&amp;L</CardTitle>
            <CardDescription>Alpaca account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className={`text-xl font-semibold ${numClass(account?.day_pl_usd ?? null)}`}>
              {account?.day_pl_usd == null ? "-" : fmtMoney(account.day_pl_usd)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Day P&amp;L %</CardTitle>
            <CardDescription>Alpaca account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className={`text-xl font-semibold ${numClass(account?.day_pl_pct ?? null)}`}>
              {account?.day_pl_pct == null ? "-" : fmtPct(account.day_pl_pct)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Buying Power</CardTitle>
            <CardDescription>Alpaca account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{account ? fmtMoney(account.buying_power) : "-"}</div>
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
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-sm text-slate-600">Loading…</div>
          ) : (
            <DataTable data={positions} columns={columns} pageSize={200} searchPlaceholder="Search positions…" />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Strategies Overview</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? <div className="text-sm text-slate-600">Loading…</div> : <DataTable data={strategies} columns={stratColumns} pageSize={200} searchPlaceholder="Search strategies…" />}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Activity (Today or Last 200)</CardTitle>
          <CardDescription>
            Each TradingView signal row shows the paired Alpaca order status (or error).
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-sm text-slate-600">Loading…</div>
          ) : (
            <DataTable data={tx} columns={txColumns} pageSize={200} searchPlaceholder="Search activity…" />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Orders (Open first)</CardTitle>
          <CardDescription>Alpaca order history, sorted so open/unfilled orders show first.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-sm text-slate-600">Loading…</div>
          ) : (
            <DataTable data={orders} columns={ordersColumns} pageSize={200} searchPlaceholder="Search orders…" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

