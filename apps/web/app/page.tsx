"use client";

import { useEffect, useState } from "react";

export default function HomePage() {
  const [health, setHealth] = useState<unknown>({ loading: true });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/health", { cache: "no-store" });
        const json = await res.json();
        if (!cancelled) setHealth(json);
      } catch {
        if (!cancelled) setHealth({ ok: false, error: "fetch_failed" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        <h1 className="text-2xl font-semibold">Schicchi Forward Testing</h1>
        <p className="mt-2 text-sm text-zinc-300">
          This UI is coming online first. Next we’ll add dashboard/compare/metrics/trades screens.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
            <div className="text-sm font-medium text-zinc-200">API Health</div>
            <pre className="mt-2 overflow-auto rounded-lg bg-black/40 p-3 text-xs text-zinc-200">
              {JSON.stringify(health, null, 2)}
            </pre>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4">
            <div className="text-sm font-medium text-zinc-200">Webhook URL (safe ports)</div>
            <div className="mt-2 text-xs text-zinc-300">
              <code>/api/webhook/tradingview</code>
            </div>
            <div className="mt-4 text-sm font-medium text-zinc-200">Next steps</div>
            <ul className="mt-2 list-disc pl-5 text-xs text-zinc-300">
              <li>Strategy/positions dashboard</li>
              <li>Trades/fills table + export</li>
              <li>Equity curve + benchmark compare</li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}

