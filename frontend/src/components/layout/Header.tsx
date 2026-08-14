'use client';

import { useState, useEffect, useCallback } from 'react';
import { Bell, Search } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { CommandPalette } from './CommandPalette';
import { NotificationDrawer } from './NotificationDrawer';
import { fetchApi } from '@/lib/api';

export function Header() {
  const { user, logout } = useAuth();
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const router = useRouter();

  const refreshUnreadCount = useCallback(async () => {
    try {
      const data = await fetchApi('/notifications?unread_only=true&page_size=1');
      setUnreadCount(data?.total ?? data?.items?.length ?? 0);
    } catch {
      setUnreadCount(0);
    }
  }, []);

  useEffect(() => {
    refreshUnreadCount();
    // Re-check every 60 seconds
    const interval = setInterval(refreshUnreadCount, 60_000);
    return () => clearInterval(interval);
  }, [refreshUnreadCount]);

  // Prefer full name from metadata, fallback to email name, fallback to User
  const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <>
      <header className="h-20 w-full flex items-center justify-between px-8 bg-transparent sticky top-0 z-30">
        <div className="flex-1 max-w-xl">
          <div
            className="relative group cursor-pointer"
            onClick={() => setIsCommandPaletteOpen(true)}
          >
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-slate-400 group-hover:text-primary transition-colors duration-200" />
            </div>
            <div className="block w-full pl-10 pr-3 py-2.5 border border-slate-200 rounded-xl bg-white text-slate-500 transition-all duration-300 sm:text-sm flex justify-between items-center group-hover:border-primary/50 shadow-sm">
              <span>Global Search...</span>
            </div>
            {/* Hidden button for the hacky global shortcut trigger in CommandPalette */}
            <button id="cmd-k-btn" className="hidden" onClick={() => setIsCommandPaletteOpen(true)} />
          </div>
        </div>

        <div className="ml-4 flex items-center space-x-6">
          <button
            onClick={() => setIsNotificationsOpen(true)}
            className="relative p-2 rounded-xl text-emerald-800/70 hover:text-emerald-950 hover:bg-emerald-50/80 transition-all duration-200"
            title="Notifications"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-white animate-pulse" />
            )}
          </button>

          <div className="relative">
            <div
              className="flex items-center space-x-3 cursor-pointer group"
              onClick={() => setIsProfileDropdownOpen(!isProfileDropdownOpen)}
            >
              <div className="w-10 h-10 rounded-full bg-primary p-[2px]">
                <div className="w-full h-full rounded-full bg-white flex items-center justify-center overflow-hidden text-lg font-bold text-primary">
                  {initial}
                </div>
              </div>
              <div className="hidden md:block">
                <p className="text-sm font-medium text-slate-800 group-hover:text-primary transition-colors">{displayName}</p>
                <p className="text-xs text-slate-500">{user?.email || 'Logged in'}</p>
              </div>
            </div>

            {isProfileDropdownOpen && (
              <div className="absolute right-0 mt-3 w-48 bg-white border border-slate-200 rounded-xl shadow-xl overflow-hidden py-1 z-50">
                <button
                  onClick={() => {
                    setIsProfileDropdownOpen(false);
                    router.push('/dashboard/profile');
                  }}
                  className="w-full text-left px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                >
                  Profile Settings
                </button>
                <button
                  onClick={() => {
                    setIsProfileDropdownOpen(false);
                    logout();
                  }}
                  className="w-full text-left px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />

      <NotificationDrawer
        isOpen={isNotificationsOpen}
        onClose={() => {
          setIsNotificationsOpen(false);
          // Refresh count after drawer closes (user may have marked as read)
          refreshUnreadCount();
        }}
      />
    </>
  );
}
