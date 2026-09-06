import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // /api/*.py is served by Vercel's Python runtime, not by Next.js.
  // Next.js only owns app/api/** (auth) and everything under app/.
};

export default nextConfig;
