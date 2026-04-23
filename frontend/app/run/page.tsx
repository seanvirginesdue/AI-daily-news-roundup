"use client";
import { useEffect, useRef, useState } from "react";

type RunStatus = "idle" | "running" | "success" | "error";

export default function RunPage() {
  const [status, setStatus]   = useState<RunStatus>("idle");
  const [logs, setLogs]       = useState<string[]>([]);
  const [lastRun, setLastRun] = useState<string>("");
  const [clearing, setClearing] = useState(false);
  const [cleared, setCleared]   = useState(false);
  const logRef  = useRef<HTMLDivElement>(null);
  const esRef   = useRef<EventSource | null>(null);

  useEffect(() => {
    fetch("/api/run").then(r => r.json()).then(d => {
      setStatus(d.status ?? "idle");
      setLastRun(d.last_run ?? "");
    });
    return () => esRef.current?.close();
  }, []);

  useEffect(() => {
    if (logRef.current)
      logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const startRun = async () => {
    setLogs([]);
    setStatus("running");

    await fetch("/api/run", { method: "POST" });

    const es = new EventSource("/api/run/stream");
    esRef.current = es;

    es.onmessage = e => {
      const data = e.data as string;
      if (data.startsWith("[DONE:")) {
        es.close();
        fetch("/api/run").then(r => r.json()).then(d => {
          setStatus(d.status ?? "success");
          setLastRun(d.last_run ?? "");
        });
      } else {
        setLogs(prev => [...prev, data]);
      }
    };

    es.onerror = () => {
      es.close();
      setStatus("error");
    };
  };

  const clearSeen = async () => {
    setClearing(true);
    await fetch("/api/seen-articles", { method: "DELETE" });
    setClearing(false);
    setCleared(true);
    setTimeout(() => setCleared(false), 2500);
  };

  const statusBadge: Record<RunStatus, string> = {
    idle:    "bg-gray-100 text-gray-600",
    running: "bg-yellow-100 text-yellow-700",
    success: "bg-green-100 text-green-700",
    error:   "bg-red-100 text-red-700",
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Run Newsletter</h1>
      <p className="text-sm text-gray-500 mb-8">Trigger a manual send and watch the live log</p>

      <div className="flex flex-wrap gap-3 mb-6">
        <button
          onClick={startRun}
          disabled={status === "running"}
          className="bg-[#d63c2f] hover:bg-[#b83326] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-6 py-2.5 rounded-lg transition-colors text-sm">
          {status === "running" ? "Running…" : "▶ Run Now"}
        </button>

        <button
          onClick={clearSeen}
          disabled={clearing}
          className="border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium px-4 py-2.5 rounded-lg transition-colors disabled:opacity-50">
          {clearing ? "Clearing…" : "Clear Seen Articles"}
        </button>
        {cleared && <span className="self-center text-sm text-green-600 font-medium">Cleared!</span>}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-medium text-gray-700">Status</p>
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full capitalize ${statusBadge[status]}`}>
            {status}
          </span>
        </div>
        <p className="text-xs text-gray-400">{lastRun || "No runs yet"}</p>
      </div>

      {logs.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Live Log</p>
          <div
            ref={logRef}
            className="bg-gray-900 rounded-xl p-4 h-80 overflow-y-auto font-mono text-xs text-green-400 space-y-0.5">
            {logs.map((line, i) => (
              <p key={i} className="whitespace-pre-wrap wrap-break-word">{line}</p>
            ))}
            {status === "running" && (
              <p className="text-yellow-400 animate-pulse">●</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
