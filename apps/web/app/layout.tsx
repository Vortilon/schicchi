import "./globals.css";

export const metadata = {
  title: "Schicchi Forward Testing",
  description: "Forward-testing dashboard for TradingView strategies backed by Alpaca fills."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <div className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-slate-900" />
              <div className="leading-tight">
                <div className="text-sm font-semibold text-slate-900">Schicchi</div>
                <div className="text-xs text-slate-500">Forward Testing</div>
              </div>
            </div>
            <nav className="flex items-center gap-4 text-sm">
              <a className="text-slate-700 hover:text-slate-900" href="/">
                Home
              </a>
              <a className="text-slate-700 hover:text-slate-900" href="/dashboard">
                Dashboard
              </a>
              <a className="text-slate-700 hover:text-slate-900" href="/strategies">
                Strategies
              </a>
            </nav>
          </div>
        </div>
        <div className="mx-auto max-w-6xl px-6 py-8">{children}</div>
      </body>
    </html>
  );
}

