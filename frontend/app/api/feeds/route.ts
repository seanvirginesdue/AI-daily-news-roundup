const API = process.env.FASTAPI_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  const res = await fetch(`${API}/feeds`, { cache: "no-store" });
  return Response.json(await res.json(), { status: res.status });
}
export async function POST(req: Request) {
  const body = await req.json();
  const res = await fetch(`${API}/feeds`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return Response.json(await res.json(), { status: res.status });
}
