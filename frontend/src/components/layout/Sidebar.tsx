'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Briefcase, FileText, MessageSquare, LayoutGrid, StickyNote, Sparkles, User, Bell } from 'lucide-react';

const navItems = [
  { icon: Home, label: 'Dashboard', href: '/dashboard' },
  { icon: FileText, label: 'Resume Vault', href: '/dashboard/resumes' },
  { icon: Briefcase, label: 'Jobs', href: '/dashboard/jobs' },
  { icon: LayoutGrid, label: 'Applications', href: '/dashboard/applications' },
  { icon: StickyNote, label: 'Notes', href: '/dashboard/notes' },
  { icon: MessageSquare, label: 'Outreach', href: '/dashboard/outreach' },
  { icon: Bell, label: 'Notifications', href: '/dashboard/notifications' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen fixed top-0 left-0 flex flex-col bg-white/75 backdrop-blur-xl border-r border-emerald-100/80 pt-6 pb-6 z-50 transition-all duration-300">
      {/* Brand Header */}
      <div className="flex items-center px-6 mb-8">
        <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 via-teal-600 to-emerald-700 shadow-md shadow-emerald-500/30 mr-3">
          <Sparkles className="w-5 h-5 text-white animate-pulse" />
        </div>
        <div>
          <h1 className="text-xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-emerald-700 via-teal-600 to-emerald-900 tracking-tight">
            Ascendra
          </h1>
          <p className="text-[10px] uppercase font-bold text-emerald-600 tracking-wider">AI Headhunting Engine</p>
        </div>
      </div>

      {/* Navigation items */}
      <nav className="flex-1 px-4 space-y-1.5">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));

          return (
            <Link
              key={item.label}
              href={item.href}
              className={`flex items-center px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden ${isActive
                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-semibold shadow-md shadow-emerald-500/25 translate-x-1'
                : 'text-emerald-900/70 hover:bg-emerald-50/80 hover:text-emerald-950 font-medium'
                }`}
            >
              <item.icon
                className={`w-5 h-5 mr-3 transition-transform duration-200 ${isActive
                  ? 'text-white scale-110'
                  : 'text-emerald-600/60 group-hover:text-emerald-700 group-hover:scale-110'
                  }`}
              />
              <span className="text-sm tracking-wide">{item.label}</span>

              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-300 shadow-sm shadow-emerald-300/60" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer / Badge */}
      <div className="px-4 mt-auto">
        <div className="p-3.5 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100/80 text-center">
          <p className="text-xs font-bold text-emerald-900">Reverse Headhunting</p>
          <p className="text-[11px] text-emerald-600/80 font-medium mt-0.5">AI Agent Active</p>
        </div>
      </div>
    </aside>
  );
}
