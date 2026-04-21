import Link from "next/link";

async function getData() {
  const base = process.env.FASTAPI_URL ?? "http://127.0.0.1:8000";
  const [cfg, seen, status] = await Promise.all([
    fetch(`${base}/config`,        { cache: "no-store" }).then(r => r.json()).catch(() => ({})),
    fetch(`${base}/seen-articles`, { cache: "no-store" }).then(r => r.json()).catch(() => ({ count: 0 })),
    fetch(`${base}/run/status`,    { cache: "no-store" }).then(r => r.json()).catch(() => ({ status: "idle" })),
  ]);
  return { cfg, seen, status };
}

export default async function Dashboard() {
  const { cfg, seen, status } = await getData();
  const feeds      = cfg?.rss_feeds?.length  ?? "—";
  const recipients = cfg?.email?.recipients?.length ?? "—";
  const seenCount  = seen?.count ?? 0;

  const statusColor: Record<string, string> = {
    idle:    "bg-gray-100 text-gray-600",
    running: "bg-yellow-100 text-yellow-700",
    success: "bg-green-100 text-green-700",
    error:   "bg-red-100 text-red-700",
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
      <p className="text-gray-500 text-sm mb-8">AI Daily News Roundup — overview</p>

      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: "RSS Feeds",       value: feeds,      href: "/feeds"      },
          { label: "Recipients",      value: recipients, href: "/recipients" },
          { label: "Articles Seen",   value: seenCount,  href: "/dashboard"  },
        ].map(({ label, value, href }) => (
          <Link key={label} href={href}
            className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow">
            <p className="text-3xl font-bold text-[#d63c2f]">{value}</p>
            <p className="text-sm text-gray-500 mt-1">{label}</p>
          </Link>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-800">Last Run</h2>
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full capitalize ${statusColor[status?.status] ?? statusColor.idle}`}>
            {status?.status ?? "idle"}
          </span>
        </div>
        <p className="text-sm text-gray-500">{status?.last_run || "No runs yet"}</p>
        {status?.last_error && (
          <p className="text-xs text-red-600 mt-2 font-mono bg-red-50 p-2 rounded">{status.last_error}</p>
        )}
      </div>

      <Link href="/run"
        className="inline-flex items-center gap-2 bg-[#d63c2f] hover:bg-[#b83326] text-white font-semibold px-6 py-3 rounded-lg transition-colors">
        ▶ Run Newsletter Now
      </Link>
    </div>
  );
}
