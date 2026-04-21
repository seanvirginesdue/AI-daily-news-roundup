"use client";
import { useEffect, useState } from "react";

type Settings = { max_articles: number; from_name: string };

export default function SettingsPage() {
  const [form, setForm]     = useState<Settings>({ max_articles: 22, from_name: "" });
  const [saved, setSaved]   = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/settings").then(r => r.json()).then(data => {
      setForm({ max_articles: data.max_articles ?? 22, from_name: data.from_name ?? "" });
      setLoading(false);
    });
  }, []);

  const save = async () => {
    await fetch("/api/settings", {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  if (loading) return <p className="text-sm text-gray-400">Loading…</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Settings</h1>
      <p className="text-sm text-gray-500 mb-8">Newsletter configuration</p>

      <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-lg">
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-1">Sender Name</label>
          <input
            value={form.from_name}
            onChange={e => setForm({ ...form, from_name: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#d63c2f]"
            placeholder="e.g. AI Task Force"
          />
          <p className="text-xs text-gray-400 mt-1">Appears as the "From" name in the email.</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">Max Articles per Run</label>
          <input
            type="number" min={1} max={50}
            value={form.max_articles}
            onChange={e => setForm({ ...form, max_articles: Number(e.target.value) })}
            className="w-32 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#d63c2f]"
          />
          <p className="text-xs text-gray-400 mt-1">Total articles fetched across all feeds.</p>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={save}
            className="bg-[#d63c2f] hover:bg-[#b83326] text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors">
            Save Settings
          </button>
          {saved && <span className="text-sm text-green-600 font-medium">Saved!</span>}
        </div>
      </div>
    </div>
  );
}
