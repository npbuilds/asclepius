/** @type {import('next').NextConfig} */
const API_BASE = process.env.ASCLEPIUS_API_BASE || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  // Proxy /api/* to the FastAPI backend so the frontend never needs CORS or
  // hardcoded base URLs. In production, set ASCLEPIUS_API_BASE to the
  // deployed API URL (e.g. https://api.asclepius.app).
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_BASE}/api/:path*` },
      { source: "/health", destination: `${API_BASE}/health` },
    ];
  },
};

module.exports = nextConfig;
