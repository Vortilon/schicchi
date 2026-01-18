export default function HomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Home</h1>
        <p className="mt-1 text-sm text-slate-600">
          Use <a className="underline underline-offset-4" href="/dashboard">Dashboard</a> for positions and{" "}
          <a className="underline underline-offset-4" href="/strategies">Strategies</a> for per-strategy reporting.
        </p>
      </div>
    </div>
  );
}

