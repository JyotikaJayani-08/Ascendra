'use client';

import { useState, useEffect, useCallback } from 'react';
import { 
  Bell, 
  CheckCheck, 
  Sparkles, 
  Mail, 
  Clock, 
  Briefcase, 
  AlertTriangle, 
  Search, 
  RefreshCw, 
  CheckCircle2,
  Inbox,
  ArrowRight
} from 'lucide-react';
import { fetchApi } from '@/lib/api';
import Link from 'next/link';

interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  entity_type?: string | null;
  entity_id?: string | null;
  created_at: string;
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'unread' | 'outreach' | 'resumes' | 'system'>('all');

  const loadNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchApi('/notifications?page=1&page_size=100');
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
    loadNotifications();
  }, [loadNotifications]);

  const handleMarkRead = async (id: string) => {
    try {
      await fetchApi(`/notifications/${id}/read`, { method: 'POST' });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) {
      console.error('Failed to mark read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await fetchApi('/notifications/read-all', { method: 'POST' });
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    } catch (err) {
      console.error('Failed to mark all read:', err);
    }
  };

  const formatTime = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / (1000 * 60));
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins} minutes ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours} hours ago`;
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays} days ago`;
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const getNotificationBadge = (type: string) => {
    switch (type) {
      case 'EMAIL_SENT':
        return { label: 'Email Sent', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' };
      case 'EMAIL_FAILED':
        return { label: 'Email Error', color: 'bg-rose-100 text-rose-800 border-rose-200' };
      case 'REPLY_RECEIVED':
        return { label: 'Outreach Reply', color: 'bg-teal-100 text-teal-800 border-teal-200' };
      case 'FOLLOW_UP_DUE':
        return { label: 'Follow Up', color: 'bg-amber-100 text-amber-800 border-amber-200' };
      case 'RESUME_PARSED':
        return { label: 'Resume Parsed', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' };
      case 'RESUME_GENERATED':
        return { label: 'AI Tailored', color: 'bg-teal-100 text-teal-800 border-teal-200' };
      case 'APPLICATION_STATUS':
        return { label: 'Application', color: 'bg-blue-100 text-blue-800 border-blue-200' };
      default:
        return { label: 'System Alert', color: 'bg-slate-100 text-slate-800 border-slate-200' };
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'EMAIL_SENT':
      case 'REPLY_RECEIVED':
        return <Mail className="w-5 h-5 text-teal-600" />;
      case 'EMAIL_FAILED':
        return <AlertTriangle className="w-5 h-5 text-rose-600" />;
      case 'RESUME_PARSED':
      case 'RESUME_GENERATED':
        return <Sparkles className="w-5 h-5 text-emerald-600" />;
      case 'APPLICATION_STATUS':
        return <Briefcase className="w-5 h-5 text-blue-600" />;
      case 'FOLLOW_UP_DUE':
        return <Clock className="w-5 h-5 text-amber-600" />;
      default:
        return <Bell className="w-5 h-5 text-emerald-600" />;
    }
  };

  const getEntityLink = (item: NotificationItem) => {
    if (item.entity_type === 'message' || item.type.includes('EMAIL')) return '/dashboard/outreach';
    if (item.entity_type === 'resume' || item.type.includes('RESUME')) return '/dashboard/resumes';
    if (item.entity_type === 'application' || item.type.includes('APPLICATION')) return '/dashboard/applications';
    return null;
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;
  const emailCount = notifications.filter(n => n.type.includes('EMAIL') || n.type.includes('REPLY')).length;
  const resumeCount = notifications.filter(n => n.type.includes('RESUME')).length;

  const filteredNotifications = notifications.filter(n => {
    const matchesSearch = searchQuery === '' || 
      n.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
      n.message.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (activeTab === 'unread') return !n.is_read;
    if (activeTab === 'outreach') return n.type.includes('EMAIL') || n.type.includes('REPLY') || n.type.includes('FOLLOW_UP');
    if (activeTab === 'resumes') return n.type.includes('RESUME');
    if (activeTab === 'system') return n.type === 'SYSTEM' || n.type.includes('APPLICATION');
    return true;
  });

  return (
    <div className="space-y-8 pb-12">
      {/* Hero Title Section */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center text-white shadow-lg shadow-emerald-500/25">
              <Bell className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-emerald-950 tracking-tight">Notification Center</h1>
              <p className="text-xs text-emerald-700/80 font-medium">Real-time outreach updates, AI processing logs, and application alerts.</p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadNotifications}
            disabled={loading}
            className="btn-secondary py-2 px-4 text-xs flex items-center space-x-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="btn-primary py-2 px-4 text-xs flex items-center space-x-2 shadow-md shadow-emerald-600/20"
            >
              <CheckCheck className="w-4 h-4" />
              <span>Mark All Read</span>
            </button>
          )}
        </div>
      </div>

      {/* Top Summary Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-5 border border-emerald-100/80 bg-white/70 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-emerald-800/70 uppercase tracking-wider">Total Alerts</p>
              <h3 className="text-2xl font-extrabold text-emerald-950 mt-1">{notifications.length}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
              <Inbox className="w-5 h-5" />
            </div>
          </div>
        </div>

        <div className="glass-card p-5 border border-amber-100/80 bg-amber-50/30 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-amber-800/70 uppercase tracking-wider">Unread</p>
              <h3 className="text-2xl font-extrabold text-amber-950 mt-1">{unreadCount}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-100/80 border border-amber-200 flex items-center justify-center text-amber-600">
              <Clock className="w-5 h-5" />
            </div>
          </div>
        </div>

        <div className="glass-card p-5 border border-teal-100/80 bg-teal-50/30 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-teal-800/70 uppercase tracking-wider">Outreach Logs</p>
              <h3 className="text-2xl font-extrabold text-teal-950 mt-1">{emailCount}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-teal-100/80 border border-teal-200 flex items-center justify-center text-teal-600">
              <Mail className="w-5 h-5" />
            </div>
          </div>
        </div>

        <div className="glass-card p-5 border border-emerald-100/80 bg-emerald-50/30 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-emerald-800/70 uppercase tracking-wider">AI Vault</p>
              <h3 className="text-2xl font-extrabold text-emerald-950 mt-1">{resumeCount}</h3>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-100/80 border border-emerald-200 flex items-center justify-center text-emerald-600">
              <Sparkles className="w-5 h-5" />
            </div>
          </div>
        </div>
      </div>

      {/* Control Bar: Search & Category Tabs */}
      <div className="glass-panel p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Category Tabs */}
        <div className="flex items-center space-x-1 w-full md:w-auto overflow-x-auto p-1 bg-emerald-100/30 rounded-xl border border-emerald-100">
          {(['all', 'unread', 'outreach', 'resumes', 'system'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-4 text-xs font-bold rounded-lg capitalize transition-all whitespace-nowrap ${
                activeTab === tab
                  ? 'bg-white text-emerald-950 shadow-sm border border-emerald-200/80'
                  : 'text-emerald-800/70 hover:text-emerald-950 hover:bg-white/50'
              }`}
            >
              {tab === 'all' && `All (${notifications.length})`}
              {tab === 'unread' && `Unread (${unreadCount})`}
              {tab === 'outreach' && 'Outreach'}
              {tab === 'resumes' && 'AI & Resumes'}
              {tab === 'system' && 'System'}
            </button>
          ))}
        </div>

        {/* Search Bar */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-emerald-600/60 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notification text..."
            className="w-full pl-9 pr-4 py-2 bg-white/80 border border-emerald-200/80 rounded-xl text-xs font-medium text-emerald-950 placeholder-emerald-800/40 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500 transition-all"
          />
        </div>
      </div>

      {/* Notifications List */}
      <div className="space-y-3">
        {loading && notifications.length === 0 ? (
          <div className="glass-panel p-12 text-center text-emerald-800/60 space-y-3">
            <RefreshCw className="w-8 h-8 animate-spin text-emerald-600 mx-auto" />
            <p className="text-sm font-semibold">Syncing notification stream...</p>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="glass-panel p-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-8 h-8 text-emerald-500/50" />
            </div>
            <h3 className="text-base font-extrabold text-emerald-950">No notifications found</h3>
            <p className="text-xs text-emerald-700/60 mt-1 max-w-sm mx-auto">
              {searchQuery 
                ? `No notifications matching "${searchQuery}". Try clearing your search.` 
                : activeTab === 'unread' 
                ? 'All notifications have been read!' 
                : 'Activity logs will automatically populate as your AI agent executes outreach tasks.'}
            </p>
          </div>
        ) : (
          filteredNotifications.map((item) => {
            const badge = getNotificationBadge(item.type);
            const link = getEntityLink(item);

            return (
              <div
                key={item.id}
                className={`glass-card p-5 border transition-all relative group flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                  !item.is_read 
                    ? 'bg-gradient-to-r from-emerald-50/90 via-teal-50/40 to-white border-emerald-200 shadow-md' 
                    : 'bg-white/70 border-emerald-100/80 hover:bg-emerald-50/30'
                }`}
              >
                <div className="flex items-start space-x-4 flex-1">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-10 h-10 rounded-2xl bg-white border border-emerald-100 shadow-sm flex items-center justify-center">
                      {getNotificationIcon(item.type)}
                    </div>
                  </div>

                  <div className="space-y-1 flex-1">
                    <div className="flex items-center flex-wrap gap-2">
                      <h4 className={`text-sm font-bold ${!item.is_read ? 'text-emerald-950' : 'text-emerald-900/80'}`}>
                        {item.title}
                      </h4>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badge.color}`}>
                        {badge.label}
                      </span>
                      {!item.is_read && (
                        <span className="bg-emerald-600 text-white text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded-md shadow-xs">
                          New
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-emerald-900/70 leading-relaxed max-w-3xl">
                      {item.message}
                    </p>

                    <p className="text-[11px] font-medium text-emerald-700/50">
                      {formatTime(item.created_at)}
                    </p>
                  </div>
                </div>

                {/* Right Side Actions */}
                <div className="flex items-center space-x-2 pt-2 sm:pt-0 border-t sm:border-t-0 border-emerald-100/60 justify-end">
                  {link && (
                    <Link
                      href={link}
                      className="py-1.5 px-3 rounded-xl text-xs font-bold text-emerald-700 hover:text-emerald-900 bg-emerald-100/50 hover:bg-emerald-100 transition-all flex items-center space-x-1"
                    >
                      <span>View</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  )}

                  {!item.is_read && (
                    <button
                      onClick={() => handleMarkRead(item.id)}
                      className="py-1.5 px-3 rounded-xl text-xs font-bold text-emerald-700 hover:text-emerald-900 bg-white border border-emerald-200/80 hover:bg-emerald-50 transition-all flex items-center space-x-1 shadow-xs"
                      title="Mark as read"
                    >
                      <CheckCheck className="w-3.5 h-3.5" />
                      <span>Read</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
