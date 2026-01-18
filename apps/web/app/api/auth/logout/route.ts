import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const SESSION_COOKIE = "schicchi_session";

export async function POST() {
  cookies().set(SESSION_COOKIE, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
    maxAge: 0
  });
  return NextResponse.json({ ok: true });
}

