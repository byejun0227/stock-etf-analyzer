import { NextRequest, NextResponse } from "next/server";

import { createSessionToken, SESSION_COOKIE, SESSION_COOKIE_OPTIONS, sessionConfigured } from "@/lib/session";

// Ported from the original auth.py check_admin_login / make_admin_user.

export async function POST(request: NextRequest) {
  if (!sessionConfigured()) {
    return NextResponse.json({ error: "SESSION_SECRET is not configured" }, { status: 500 });
  }

  const body = await request.json().catch(() => ({}) as Record<string, unknown>);
  const id = String(body.id ?? "").trim();
  const password = String(body.password ?? "").trim();

  const expectedId = process.env.ADMIN_ID?.trim() || "admin";
  const expectedPw = process.env.ADMIN_PW?.trim() || "admin1234";

  if (id !== expectedId || password !== expectedPw) {
    return NextResponse.json({ error: "invalid credentials" }, { status: 401 });
  }

  const token = await createSessionToken({
    provider: "admin",
    email: "",
    name: "관리자",
    isAdmin: true,
  });

  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, token, SESSION_COOKIE_OPTIONS);
  return response;
}
