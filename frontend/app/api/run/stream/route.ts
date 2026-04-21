export const runtime = "edge";

const API = process.env.FASTAPI_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  const upstream = await fetch(`${API}/run/stream`, { cache: "no-store" });
  return new Response(upstream.body, {
    headers: {
      "Content-Type":  "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection":    "keep-alive",
    },
  });
}
