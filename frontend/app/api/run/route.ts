const API = process.env.FASTAPI_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  const res = await fetch(`${API}/run/status`, { cache: "no-store" });
  return Response.json(await res.json(), { status: res.status });
}
export async function POST() {
  const res = await fetch(`${API}/run`, { method: "POST" });
  return Response.json(await res.json(), { status: res.status });
}
