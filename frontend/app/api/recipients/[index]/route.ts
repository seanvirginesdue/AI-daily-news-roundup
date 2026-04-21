const API = process.env.FASTAPI_URL ?? "http://127.0.0.1:8000";

export async function PUT(req: Request, { params }: { params: Promise<{ index: string }> }) {
  const { index } = await params;
  const body = await req.json();
  const res = await fetch(`${API}/recipients/${index}`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return Response.json(await res.json(), { status: res.status });
}
export async function DELETE(_: Request, { params }: { params: Promise<{ index: string }> }) {
  const { index } = await params;
  const res = await fetch(`${API}/recipients/${index}`, { method: "DELETE" });
  return Response.json(await res.json(), { status: res.status });
}
