import bcrypt from "bcryptjs";
import { NextRequest, NextResponse } from "next/server";

import { createUser, findUserByEmail, isDbConfigured } from "@/lib/db";
import { createSessionToken, SESSION_COOKIE, SESSION_COOKIE_OPTIONS, sessionConfigured } from "@/lib/session";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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
  const name = String(body.name ?? "").trim();

  if (!EMAIL_RE.test(email)) {
    return NextResponse.json({ error: "invalid_email" }, { status: 400 });
  }
  if (password.length < 8) {
    return NextResponse.json({ error: "weak_password" }, { status: 400 });
  }
  if (!name) {
    return NextResponse.json({ error: "name_required" }, { status: 400 });
  }

  const existing = await findUserByEmail(email);
  if (existing) {
    return NextResponse.json({ error: "email_taken" }, { status: 409 });
  }

  const passwordHash = await bcrypt.hash(password, 10);
  const user = await createUser(email, passwordHash, name);

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
