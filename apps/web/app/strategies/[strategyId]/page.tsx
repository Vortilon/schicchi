"use client";

import { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";

import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtMoney, fmtPct, numClass } from "@/lib/format";

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

type StrategyReport = {
  error?: string;
  strategy: {
    id: string;
    name: string;
    is_active: boolean;
    sizing_type: string;
    basis_per_symbol_usd: number;
  };
  summary: {
    symbols_traded: number;
    signals_total: number;
    open_positions_count: number;
    trades_total: number;
    wins: number;
    losses: number;
    win_rate: number | null;
    pnl_usd: number;
    pnl_pct: number | null;
    gross_profit_usd: number;
    gross_loss_usd: number;
    profit_factor: number | null;
    max_drawdown_pct: number | null;
    buy_hold_basis_usd: number | null;
    buy_hold_usd: number | null;
    buy_hold_pct: number | null;
  };
  by_symbol: Array<{
    symbol: string;
    signals: number;
    open_qty: number;
    avg_entry_price: number | null;
    filled_orders: number;
    trades_total: number;
    wins: number;
    losses: number;
    win_rate: number | null;
    net_profit_usd: number;
    profit_factor: number | null;
    buy_hold_pct: number | null;
    buy_hold_usd: number | null;
  }>;
  notes?: string[];
};

export default function StrategyDetailPage({ params }: { params: { strategyId: string } }) {
  const strategyId = params.strategyId;

  const [trades, setTrades] = useState<TradeRow[]>([]);
  const [report, setReport] = useState<StrategyReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [tradesRes, reportRes] = await Promise.all([
          fetch(`/api/trades?strategy_id=${encodeURIComponent(strategyId)}`, { cache: "no-store" }),
          fetch(`/api/strategies/${encodeURIComponent(strategyId)}/report`, { cache: "no-store" })
        ]);
        const tradesJson = await tradesRes.json();
        const reportJson = await reportRes.json();
        if (!cancelled) {
          setTrades(Array.isArray(tradesJson) ? tradesJson : []);
          setReport(reportJson && typeof reportJson === "object" ? (reportJson as StrategyReport) : null);
        }
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

  const bySymbolColumns = useMemo<ColumnDef<StrategyReport["by_symbol"][number]>[]>(
    () => [
      { accessorKey: "symbol", header: "Symbol" },
      { accessorKey: "signals", header: "Signals" },
      { accessorKey: "filled_orders", header: "Filled Orders" },
      {
        accessorKey: "open_qty",
        header: "Open Qty",
        cell: ({ row }) => (row.original.open_qty === 0 ? "-" : row.original.open_qty)
      },
      {
        accessorKey: "net_profit_usd",
        header: "Net P&L $",
        cell: ({ row }) => <span className={numClass(row.original.net_profit_usd)}>{fmtMoney(row.original.net_profit_usd)}</span>
      },
      { accessorKey: "trades_total", header: "Trades" },
      { accessorKey: "wins", header: "Wins" },
      { accessorKey: "losses", header: "Losses" },
      {
        accessorKey: "win_rate",
        header: "Win %",
        cell: ({ row }) => (row.original.win_rate == null ? "-" : fmtPct(row.original.win_rate))
      },
      {
        accessorKey: "profit_factor",
        header: "PF",
        cell: ({ row }) => (row.original.profit_factor == null ? "-" : row.original.profit_factor.toFixed(2))
      },
      {
        accessorKey: "buy_hold_pct",
        header: "B&H %",
        cell: ({ row }) => (row.original.buy_hold_pct == null ? "-" : fmtPct(row.original.buy_hold_pct))
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
          <CardTitle>Summary (numbers-only)</CardTitle>
          <CardDescription>
            Computed per symbol first, then rolled up. Trades are counted when a symbol position returns to flat.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-sm text-slate-600">Loading…</div>
          ) : report?.error ? (
            <div className="text-sm text-slate-600">Report error: {report.error}</div>
          ) : report ? (
            <div className="grid gap-4 md:grid-cols-6">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="text-xs text-slate-500">Symbols</div>
                <div className="text-xl font-semibold text-slate-900">{report.summary.symbols_traded}</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="text-xs text-slate-500">Trades</div>
                <div className="text-xl font-semibold text-slate-900">{report.summary.trades_total}</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="text-xs text-slate-500">Win rate</div>
                <div className="text-xl font-semibold text-slate-900">{report.summary.win_rate == null ? "-" : fmtPct(report.summary.win_rate)}</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="text-xs text-slate-500">Net P&amp;L</div>
                <div className={`text-xl font-semibold ${numClass(report.summary.pnl_usd)}`}>{fmtMoney(report.summary.pnl_usd)}</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="text-xs text-slate-500">Profit factor</div>
                <div className="text-xl font-semibold text-slate-900">{report.summary.profit_factor == null ? "-" : report.summary.profit_factor.toFixed(2)}</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="text-xs text-slate-500">Max drawdown</div>
                <div className="text-xl font-semibold text-slate-900">
                  {report.summary.max_drawdown_pct == null ? "-" : fmtPct(report.summary.max_drawdown_pct)}
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4 md:col-span-3">
                <div className="text-xs text-slate-500">Buy &amp; Hold (same period)</div>
                <div className="mt-1 text-sm text-slate-900">
                  {report.summary.buy_hold_pct == null ? "-" : fmtPct(report.summary.buy_hold_pct)}{" "}
                  {report.summary.buy_hold_usd == null ? "" : `(${fmtMoney(report.summary.buy_hold_usd)})`}
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4 md:col-span-3">
                <div className="text-xs text-slate-500">Notes</div>
                <div className="mt-1 text-sm text-slate-700">
                  {(report.notes ?? []).slice(0, 2).join(" ")}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-600">No report data yet.</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Per-symbol breakdown</CardTitle>
          <CardDescription>
            This is the “fix” for mixed-symbol math: each symbol is computed independently, then totals are rolled up.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-sm text-slate-600">Loading…</div>
          ) : report?.by_symbol?.length ? (
            <DataTable data={report.by_symbol} columns={bySymbolColumns} pageSize={25} searchPlaceholder="Search symbols…" />
          ) : (
            <div className="text-sm text-slate-600">No symbol rows yet.</div>
          )}
        </CardContent>
      </Card>

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

