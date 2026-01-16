import "./globals.css";

export const metadata = {
  title: "Schicchi Forward Testing",
  description: "Forward-testing dashboard for TradingView strategies backed by Alpaca fills."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-100">{children}</body>
    </html>
  );
}

