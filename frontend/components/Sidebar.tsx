"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/dashboard",  label: "Dashboard",   icon: "▦" },
  { href: "/run",        label: "Run Now",      icon: "▶" },
  { href: "/feeds",      label: "RSS Feeds",    icon: "◈" },
  { href: "/recipients", label: "Recipients",   icon: "✉" },
  { href: "/settings",   label: "Settings",     icon: "⚙" },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-56 min-h-screen bg-white border-r border-gray-200 flex flex-col">
      <div className="px-5 py-5 border-b border-gray-100">
        <span className="text-sm font-bold text-gray-400 uppercase tracking-widest">AI Daily News</span>
      </div>
      <nav className="flex-1 py-4 px-3 space-y-1">
        {nav.map(({ href, label, icon }) => {
          const active = path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                ${active
                  ? "bg-red-50 text-[#d63c2f]"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"}`}
            >
              <span className="text-base w-5 text-center">{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-5 py-4 border-t border-gray-100">
        <p className="text-xs text-gray-400">Boulder SEO Marketing</p>
      </div>
    </aside>
  );
}
