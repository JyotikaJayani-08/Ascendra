'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { 
  X, 
  Bell, 
  CheckCircle2, 
  Clock, 
  FileText, 
  Mail, 
  AlertTriangle, 
  MessageSquare, 
  Briefcase, 
  Sparkles,
  CheckCheck,
  ExternalLink,
  RefreshCw
} from 'lucide-react';
import { fetchApi } from '@/lib/api';

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  entity_type?: string | null;
  entity_id?: string | null;
  created_at: string;
}

export function NotificationDrawer({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'unread' | 'outreach' | 'resumes'>('all');

  const loadNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchApi('/notifications?page=1&page_size=50');
      if (Array.isArray(data)) {
        setNotifications(data);
      }
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadNotifications();
    }
  }, [isOpen, loadNotifications]);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const handleMarkRead = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      await fetchApi(`/notifications/${id}/read`, { method: 'POST' });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await fetchApi('/notifications/read-all', { method: 'POST' });
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  };

  const formatTimeAgo = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / (1000 * 60));
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays}d ago`;
    } catch {
      return dateStr;
    }
  };

  const getNotificationIcon = (type: string, isRead: boolean) => {
    switch (type) {
      case 'EMAIL_SENT':
      case 'REPLY_RECEIVED':
        return (
          <div className={`p-2 rounded-xl ${isRead ? 'bg-teal-50 text-teal-600' : 'bg-teal-100 text-teal-700 shadow-sm'}`}>
            <Mail className="w-4 h-4" />
          </div>
        );
      case 'EMAIL_FAILED':
        return (
          <div className="p-2 rounded-xl bg-rose-50 text-rose-600 shadow-sm">
            <AlertTriangle className="w-4 h-4" />
          </div>
        );
      case 'RESUME_PARSED':
      case 'RESUME_GENERATED':
        return (
          <div className={`p-2 rounded-xl ${isRead ? 'bg-emerald-50 text-emerald-600' : 'bg-emerald-100 text-emerald-700 shadow-sm'}`}>
            <Sparkles className="w-4 h-4" />
          </div>
        );
      case 'APPLICATION_STATUS':
        return (
          <div className={`p-2 rounded-xl ${isRead ? 'bg-emerald-50 text-emerald-600' : 'bg-emerald-100 text-emerald-700 shadow-sm'}`}>
            <Briefcase className="w-4 h-4" />
          </div>
        );
      case 'FOLLOW_UP_DUE':
        return (
          <div className="p-2 rounded-xl bg-amber-50 text-amber-600 shadow-sm">
            <Clock className="w-4 h-4" />
          </div>
        );
      default:
        return (
          <div className={`p-2 rounded-xl ${isRead ? 'bg-emerald-50 text-emerald-600' : 'bg-emerald-100 text-emerald-700 shadow-sm'}`}>
            <Bell className="w-4 h-4" />
          </div>
        );
    }
  };

  const filteredNotifications = notifications.filter(n => {
    if (activeFilter === 'unread') return !n.is_read;
    if (activeFilter === 'outreach') return n.type.includes('EMAIL') || n.type.includes('REPLY') || n.type.includes('FOLLOW_UP');
    if (activeFilter === 'resumes') return n.type.includes('RESUME');
    return true;
  });

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-emerald-950/20 backdrop-blur-md z-40 transition-opacity animate-in fade-in duration-200"
          onClick={onClose}
        />
      )}

      {/* Drawer Panel */}
      <div 
        className={`fixed top-0 right-0 h-full w-full sm:w-96 bg-white/95 backdrop-blur-2xl border-l border-emerald-100 shadow-2xl z-50 transform transition-transform duration-300 ease-out flex flex-col ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-5 border-b border-emerald-100/80 bg-gradient-to-r from-emerald-50/50 to-teal-50/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
                <Bell className="w-4 h-4 animate-pulse" />
              </div>
              <div>
                <h2 className="text-base font-extrabold text-emerald-950 tracking-tight">Notifications</h2>
                <p className="text-[11px] text-emerald-700/70 font-medium">Activity & Agent Intelligence</p>
              </div>
              {unreadCount > 0 && (
                <span className="ml-1 bg-emerald-600 text-white text-[11px] font-bold px-2 py-0.5 rounded-full shadow-sm">
                  {unreadCount}
                </span>
              )}
            </div>
            
            <div className="flex items-center space-x-1">
              <button 
                onClick={loadNotifications} 
                className="p-2 text-emerald-700/60 hover:text-emerald-900 hover:bg-emerald-100/50 rounded-xl transition-all"
                title="Refresh notifications"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
              <button 
                onClick={onClose}
                className="p-2 text-emerald-700/60 hover:text-emerald-900 hover:bg-emerald-100/50 rounded-xl transition-all"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex space-x-1 mt-4 p-1 bg-emerald-100/40 rounded-xl border border-emerald-100">
            {(['all', 'unread', 'outreach', 'resumes'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveFilter(tab)}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg capitalize transition-all ${
                  activeFilter === tab 
                    ? 'bg-white text-emerald-950 shadow-sm border border-emerald-200/60' 
                    : 'text-emerald-800/70 hover:text-emerald-950'
                }`}
              >
                {tab === 'resumes' ? 'AI & Vault' : tab}
              </button>
            ))}
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto divide-y divide-emerald-50">
          {loading && notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-emerald-700/60 space-y-3">
              <RefreshCw className="w-7 h-7 animate-spin text-emerald-600" />
              <p className="text-xs font-medium">Fetching updates...</p>
            </div>
          ) : filteredNotifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-center px-6">
              <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-3">
                <CheckCircle2 className="w-7 h-7 text-emerald-600/40" />
              </div>
              <p className="text-sm font-bold text-emerald-950">You&apos;re all caught up!</p>
              <p className="text-xs text-emerald-700/60 mt-1 max-w-[200px]">
                {activeFilter === 'unread' 
                  ? 'No unread notifications right now.' 
                  : 'New outreach activity and resume updates will appear here.'}
              </p>
            </div>
          ) : (
            filteredNotifications.map(item => (
              <div 
                key={item.id} 
                onClick={() => !item.is_read && handleMarkRead(item.id)}
                className={`p-4 transition-all hover:bg-emerald-50/40 cursor-pointer group relative flex items-start space-x-3 ${
                  !item.is_read ? 'bg-emerald-50/70' : 'bg-transparent'
                }`}
              >
                {/* Icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {getNotificationIcon(item.type, item.is_read)}
                </div>

                {/* Body */}
                <div className="flex-1 min-w-0 pr-4">
                  <div className="flex items-center justify-between">
                    <p className={`text-xs font-bold ${!item.is_read ? 'text-emerald-950' : 'text-emerald-900/80'}`}>
                      {item.title}
                    </p>
                    <span className="text-[10px] font-medium text-emerald-700/60 flex-shrink-0 ml-2">
                      {formatTimeAgo(item.created_at)}
                    </span>
                  </div>
                  <p className="text-xs text-emerald-800/70 mt-1 line-clamp-2 leading-relaxed">
                    {item.message}
                  </p>
                </div>

                {/* Unread indicator / mark read button */}
                {!item.is_read && (
                  <button
                    onClick={(e) => handleMarkRead(item.id, e)}
                    className="absolute top-4 right-3 w-2 h-2 rounded-full bg-emerald-600 group-hover:w-4 group-hover:h-4 group-hover:rounded-lg group-hover:bg-emerald-100 group-hover:text-emerald-700 flex items-center justify-center transition-all shadow-sm"
                    title="Mark read"
                  >
                    <span className="hidden group-hover:inline text-[9px] font-bold">✓</span>
                  </button>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-emerald-100 bg-emerald-50/40 space-y-2">
          {unreadCount > 0 && (
            <button 
              onClick={handleMarkAllRead}
              className="w-full py-2 px-3 text-xs font-bold text-emerald-700 hover:text-emerald-900 bg-white hover:bg-emerald-100/50 border border-emerald-200/80 rounded-xl transition-all flex items-center justify-center space-x-1.5 shadow-sm"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              <span>Mark all as read</span>
            </button>
          )}

          <Link
            href="/dashboard/notifications"
            onClick={onClose}
            className="w-full py-2.5 px-3 text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 rounded-xl transition-all flex items-center justify-center space-x-1.5 shadow-md shadow-emerald-600/20"
          >
            <span>Open Notification Center</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </>
  );
}

