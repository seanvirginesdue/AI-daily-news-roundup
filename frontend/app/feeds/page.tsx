"use client";
import { useEffect, useState } from "react";

type Feed = { name: string; url: string };

export default function FeedsPage() {
  const [feeds, setFeeds]     = useState<Feed[]>([]);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft]     = useState<Feed>({ name: "", url: "" });
  const [adding, setAdding]   = useState(false);
  const [newFeed, setNewFeed] = useState<Feed>({ name: "", url: "" });

  const load = () =>
    fetch("/api/feeds").then(r => r.json()).then(setFeeds);

  useEffect(() => { load(); }, []);

  const save = async (i: number) => {
    await fetch(`/api/feeds/${i}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    });
    setEditing(null); load();
  };

  const del = async (i: number) => {
    if (!confirm("Remove this feed?")) return;
    await fetch(`/api/feeds/${i}`, { method: "DELETE" });
    load();
  };

  const add = async () => {
    if (!newFeed.name || !newFeed.url) return;
    await fetch("/api/feeds", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newFeed),
    });
    setAdding(false); setNewFeed({ name: "", url: "" }); load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">RSS Feeds</h1>
          <p className="text-sm text-gray-500 mt-0.5">{feeds.length} feeds configured</p>
        </div>
        <button onClick={() => setAdding(true)}
          className="bg-[#d63c2f] hover:bg-[#b83326] text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors">
          + Add Feed
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        {feeds.map((f, i) => (
          <div key={i} className="px-5 py-4">
            {editing === i ? (
              <div className="flex gap-2 items-center">
                <input value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })}
                  placeholder="Name" className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-[#d63c2f]" />
                <input value={draft.url} onChange={e => setDraft({ ...draft, url: e.target.value })}
                  placeholder="URL" className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm flex-1 focus:outline-none focus:ring-2 focus:ring-[#d63c2f]" />
                <button onClick={() => save(i)} className="bg-[#d63c2f] text-white text-sm px-3 py-1.5 rounded-lg">Save</button>
                <button onClick={() => setEditing(null)} className="text-gray-400 text-sm px-3 py-1.5 rounded-lg hover:bg-gray-50">Cancel</button>
              </div>
            ) : (
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="font-medium text-sm text-gray-900">{f.name}</p>
                  <p className="text-xs text-gray-400 truncate mt-0.5">{f.url}</p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => { setEditing(i); setDraft(f); }}
                    className="text-xs text-gray-500 hover:text-gray-800 px-2 py-1 rounded hover:bg-gray-50">Edit</button>
                  <button onClick={() => del(i)}
                    className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50">Delete</button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {adding && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <h2 className="font-bold text-lg mb-4">Add RSS Feed</h2>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input value={newFeed.name} onChange={e => setNewFeed({ ...newFeed, name: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-[#d63c2f]"
              placeholder="e.g. TechCrunch AI" />
            <label className="block text-sm font-medium text-gray-700 mb-1">Feed URL</label>
            <input value={newFeed.url} onChange={e => setNewFeed({ ...newFeed, url: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-5 focus:outline-none focus:ring-2 focus:ring-[#d63c2f]"
              placeholder="https://..." />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setAdding(false)} className="text-sm text-gray-500 px-4 py-2 rounded-lg hover:bg-gray-50">Cancel</button>
              <button onClick={add} className="bg-[#d63c2f] text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#b83326]">Add Feed</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
