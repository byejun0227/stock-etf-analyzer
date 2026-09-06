import { neon, type NeonQueryFunction } from "@neondatabase/serverless";

// Lazy init: DATABASE_URL may not exist yet at build time (e.g. before the
// Neon Marketplace integration is connected), and `neon()` throws immediately
// if called with an empty string. Next.js evaluates top-level module code
// during `next build`, so this must not run until a request actually needs it.
let _sql: NeonQueryFunction<false, false> | null = null;

function getSql(): NeonQueryFunction<false, false> {
  if (!_sql) {
    const url = process.env.DATABASE_URL;
    if (!url) throw new Error("DATABASE_URL is not configured");
    _sql = neon(url);
  }
  return _sql;
}

let _schemaReady: Promise<void> | null = null;

function ensureSchema(): Promise<void> {
  if (!_schemaReady) {
    const sql = getSql();
    _schemaReady = sql`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
      )
    `.then(() => undefined);
  }
  return _schemaReady;
}

export interface DbUser {
  id: number;
  email: string;
  password_hash: string;
  name: string;
}

export async function findUserByEmail(email: string): Promise<DbUser | null> {
  await ensureSchema();
  const sql = getSql();
  const rows = await sql`SELECT id, email, password_hash, name FROM users WHERE email = ${email} LIMIT 1`;
  return (rows[0] as DbUser) ?? null;
}

export async function createUser(email: string, passwordHash: string, name: string): Promise<DbUser> {
  await ensureSchema();
  const sql = getSql();
  const rows = await sql`
    INSERT INTO users (email, password_hash, name)
    VALUES (${email}, ${passwordHash}, ${name})
    RETURNING id, email, password_hash, name
  `;
  return rows[0] as DbUser;
}

export function isDbConfigured(): boolean {
  return !!process.env.DATABASE_URL;
}
