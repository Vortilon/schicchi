import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import crypto from "crypto";

const SESSION_COOKIE = "schicchi_session";

export async function POST(req: Request) {
  const { username, password } = (await req.json().catch(() => ({}))) as {
    username?: string;
    password?: string;
  };

  if (!username || !password) {
    return NextResponse.json({ ok: false, error: "missing_credentials" }, { status: 400 });
  }

  const expectedUser = process.env.UI_BASIC_AUTH_USER || "otto";
  const expectedPass = process.env.UI_BASIC_AUTH_PASSWORD || "";

  if (!expectedPass) {
    return NextResponse.json({ ok: false, error: "server_not_configured" }, { status: 500 });
  }

  if (username !== expectedUser || password !== expectedPass) {
    return NextResponse.json({ ok: false, error: "invalid_credentials" }, { status: 401 });
  }

  const sessionSecret = process.env.UI_SESSION_SECRET || expectedPass;
  const token = crypto.createHmac("sha256", sessionSecret).update(`${username}:${Date.now()}`).digest("hex");

  cookies().set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
    maxAge: 60 * 60 * 24 * 30 // 30 days
  });

  return NextResponse.json({ ok: true });
}

