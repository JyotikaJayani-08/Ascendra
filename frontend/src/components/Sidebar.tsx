"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  FileText, 
  Briefcase, 
  Users, 
  Mail, 
  Settings,
  Bot
} from "lucide-react";

import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Resumes", href: "/resumes", icon: FileText },
  { name: "Applications", href: "/applications", icon: Briefcase },
  { name: "Network", href: "/network", icon: Users },
  { name: "Outreach", href: "/outreach", icon: Mail },
  { name: "AI Prompts", href: "/prompts", icon: Bot },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white dark:bg-[#0B0F19] border-r border-gray-200 dark:border-gray-800 hidden md:flex flex-col h-screen sticky top-0 z-40">
      <div className="h-16 flex items-center px-6 border-b border-gray-200 dark:border-gray-800">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <span className="text-white font-bold text-xl">A</span>
          </div>
          <span className="text-xl font-bold tracking-tight text-gray-900 dark:text-white">
            Ascendra
          </span>
        </Link>
      </div>
      
      <WorkspaceSwitcher />

      <div className="flex-1 overflow-y-auto py-6 px-3">
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400"
                    : "text-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/50 hover:text-gray-900 dark:hover:text-gray-100"
                }`}
              >
                <item.icon
                  className={`flex-shrink-0 w-5 h-5 mr-3 ${
                    isActive ? "text-indigo-700 dark:text-indigo-400" : "text-gray-400 dark:text-gray-500"
                  }`}
                  aria-hidden="true"
                />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-gray-200 dark:border-gray-800">
        <Link
          href="/settings"
          className="flex items-center px-3 py-2.5 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors"
        >
          <Settings className="flex-shrink-0 w-5 h-5 mr-3 text-gray-400 dark:text-gray-500" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
