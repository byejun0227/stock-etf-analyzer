import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";

export interface SessionUser {
  provider: "google" | "kakao" | "admin";
  email: string;
  name: string;
  isAdmin: boolean;
}

export const SESSION_COOKIE = "session";
const MAX_AGE_SECONDS = 60 * 60 * 24 * 30; // 30 days

function getSecretKey(): Uint8Array | null {
  const secret = process.env.SESSION_SECRET;
  if (!secret) return null;
  return new TextEncoder().encode(secret);
}

export function sessionConfigured(): boolean {
  return getSecretKey() !== null;
}

export async function createSessionToken(user: SessionUser): Promise<string> {
  const key = getSecretKey();
  if (!key) throw new Error("SESSION_SECRET is not configured");
  return new SignJWT({ ...user })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${MAX_AGE_SECONDS}s`)
    .sign(key);
}

export async function verifySessionToken(token: string): Promise<SessionUser | null> {
  const key = getSecretKey();
  if (!key) return null;
  try {
    const { payload } = await jwtVerify(token, key);
    return payload as unknown as SessionUser;
  } catch {
    return null;
  }
}

export async function getSession(): Promise<SessionUser | null> {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!token) return null;
  return verifySessionToken(token);
}

export const SESSION_COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
  maxAge: MAX_AGE_SECONDS,
};
