import { NextRequest, NextResponse } from "next/server";

function unauthorized() {
  return new NextResponse("Unauthorized", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Schicchi"' }
  });
}

export function middleware(req: NextRequest) {
  const user = process.env.UI_BASIC_AUTH_USER || "otto";
  const pass = process.env.UI_BASIC_AUTH_PASSWORD || "";

  // If no password is set, do not allow access (force you to configure it).
  if (!pass) return unauthorized();

  const auth = req.headers.get("authorization") || "";
  if (!auth.startsWith("Basic ")) return unauthorized();

  const decoded = Buffer.from(auth.slice("Basic ".length), "base64").toString();
  const [u, p] = decoded.split(":");

  if (u !== user || p !== pass) return unauthorized();
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api).*)"]
};

