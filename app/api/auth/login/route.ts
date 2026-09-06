import bcrypt from "bcryptjs";
import { NextRequest, NextResponse } from "next/server";

import { findUserByEmail, isDbConfigured } from "@/lib/db";
import { createSessionToken, SESSION_COOKIE, SESSION_COOKIE_OPTIONS, sessionConfigured } from "@/lib/session";

export async function POST(request: NextRequest) {
  if (!sessionConfigured()) {
    return NextResponse.json({ error: "SESSION_SECRET is not configured" }, { status: 500 });
  }
  if (!isDbConfigured()) {
    return NextResponse.json({ error: "database is not configured" }, { status: 500 });
  }

  const body = await request.json().catch(() => ({}) as Record<string, unknown>);
  const email = String(body.email ?? "").trim().toLowerCase();
  const password = String(body.password ?? "");

  const user = await findUserByEmail(email);
  if (!user) {
    return NextResponse.json({ error: "invalid_credentials" }, { status: 401 });
  }

  const ok = await bcrypt.compare(password, user.password_hash);
  if (!ok) {
    return NextResponse.json({ error: "invalid_credentials" }, { status: 401 });
  }

  const token = await createSessionToken({
    provider: "local",
    email: user.email,
    name: user.name,
    isAdmin: false,
  });
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, token, SESSION_COOKIE_OPTIONS);
  return response;
}
