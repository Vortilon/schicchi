"use client";

import Image from "next/image";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function LoginPage({ searchParams }: { searchParams?: { next?: string } }) {
  // Avoid useSearchParams() to keep Next build/prerender happy in Docker.
  const next = searchParams?.next || "/dashboard";

  const [username, setUsername] = useState("otto");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  return (
    <div className="grid min-h-[70vh] gap-8 md:grid-cols-2">
      <div className="hidden items-center justify-center md:flex">
        <div className="w-full max-w-[620px]">
          <div className="relative aspect-[16/10] w-full overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <Image src="/splash.png" alt="Splash" fill className="object-contain p-6" priority />
          </div>
          <div className="mt-4 text-center">
            <div className="text-lg font-semibold text-slate-900">Schicchi</div>
            <div className="text-sm text-slate-600">Forward Testing Dashboard</div>
          </div>
        </div>
      </div>

      <div className="flex items-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Sign in</CardTitle>
            <CardDescription>Use your Schicchi username and password.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="text-sm font-medium text-slate-700">Username</div>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-slate-700">Password</div>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>

            {error ? <div className="text-sm text-red-600">{error}</div> : null}

            <Button
              className="w-full"
              disabled={loading}
              onClick={async () => {
                setLoading(true);
                setError(null);
                try {
                  const res = await fetch("/api/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, password })
                  });
                  const json = await res.json().catch(() => ({}));
                  if (!res.ok) {
                    setError(json?.error === "invalid_credentials" ? "Wrong username or password." : "Login failed.");
                    return;
                  }
                  window.location.href = next;
                } finally {
                  setLoading(false);
                }
              }}
            >
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

