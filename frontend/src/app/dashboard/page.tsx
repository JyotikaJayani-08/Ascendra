'use client';

import { useEffect, useState } from 'react';
import { BarChart3, Users, Briefcase, FileText, Loader2, Search, Sparkles, TrendingUp, CheckCircle2, Bell, Mail, Zap } from 'lucide-react';
import { fetchApi } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

interface PipelineStats {
  draft: number;
  ready: number;
  sent: number;
  delivered: number;
  reply_received: number;
  interview: number;
  offer: number;
  rejected: number;
  total: number;
}

interface DashboardOverview {
  pipeline: PipelineStats;
  total_resumes: number;
  total_resume_versions: number;
  total_conversations: number;
  total_messages_sent: number;
  pending_approvals: number;
  communication?: {
    emails_sent: number;
    emails_delivered: number;
    emails_failed: number;
    replies_received: number;
    reply_rate: number;
    pending_followups: number;
  };
  ai_metrics?: {
    total_generations: number;
    total_tokens_used: number;
    resume_generations: number;
    email_generations: number;
  };
}

interface Notification {
  id: string;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

interface FunnelVelocityMetrics {
  avg_days_in_draft: number;
  avg_days_to_interview: number;
  avg_days_to_offer: number;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [velocity, setVelocity] = useState<FunnelVelocityMetrics | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const [dashboardResult, velocityResult, notifResult] = await Promise.all([
          fetchApi('/dashboard'),
          fetchApi('/dashboard/funnel-velocity').catch(() => null),
          fetchApi('/notifications').catch(() => []),
        ]);
        setData(dashboardResult);
        setVelocity(velocityResult);

        const notifItems = notifResult.items || notifResult || [];
        setNotifications(Array.isArray(notifItems) ? notifItems.slice(0, 5) : []);
      } catch (error) {
        console.error('Failed to load dashboard:', error);
      } finally {
        setLoading(false);
      }
    };
    
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  const stats = [
    { name: 'Active Applications', value: data?.pipeline.total ?? 0, icon: Briefcase, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200/80' },
    { name: 'Interviews Scheduled', value: data?.pipeline.interview ?? 0, icon: BarChart3, color: 'text-teal-600', bg: 'bg-teal-50', border: 'border-teal-200/80' },
    { name: 'Network Contacts', value: data?.total_conversations ?? 0, icon: Users, color: 'text-emerald-700', bg: 'bg-emerald-50/80', border: 'border-emerald-200/80' },
    { name: 'Tailored Resumes', value: data?.total_resume_versions ?? 0, icon: FileText, color: 'text-teal-700', bg: 'bg-teal-50/80', border: 'border-teal-200/80' },
  ];

  const formatTimeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      {/* Header Greeting */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-emerald-950 mb-1 flex items-center">
            Welcome back, {(user?.user_metadata?.full_name as string)?.split(' ')[0] || 'there'}! 👋
          </h2>
          <p className="text-emerald-900/70 font-medium">Your AI reverse headhunting agent is actively tracking positions.</p>
        </div>
        
        <div
          className="relative w-full sm:w-64 lg:w-80 cursor-pointer group"
          onClick={() => {
            const btn = document.getElementById('cmd-k-btn');
            if (btn) btn.click();
          }}
        >
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-emerald-600/50 group-hover:text-emerald-600 transition-colors" />
          </div>
          <div
            className="block w-full pl-10 pr-3 py-2 border border-emerald-200/80 rounded-xl text-slate-400 bg-white/90 sm:text-sm transition-all shadow-sm group-hover:border-emerald-400 group-hover:shadow-md flex items-center"
          >
            Search applications & jobs...
          </div>
        </div>
      </div>

      {/* Informative Header Banner */}
      <div className="bg-gradient-to-r from-emerald-900/90 to-teal-900/90 text-white p-4 rounded-2xl shadow-md border border-emerald-700/50">
        <div className="flex items-start space-x-3">
          <div className="p-2 bg-emerald-500/20 rounded-xl mt-0.5">
            <Sparkles className="w-5 h-5 text-emerald-300" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-emerald-100">Ascendra Command Center Overview</h3>
            <p className="text-xs text-emerald-200/80 mt-0.5 leading-relaxed">
              Real-time analytics aggregating your <strong>Target Jobs, Application Pipeline, and Outreach Network</strong>. As you save positions, tailor resumes with AI, and advance cards on the Pipeline board, your <strong>Funnel Velocity</strong> and response metrics update automatically!
            </p>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div>
      {/* Top Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <div key={i} className={`glass-card p-5 border ${stat.border} flex flex-col justify-between group hover:-translate-y-1 transition-all duration-300 shadow-md shadow-emerald-500/5`}>
            <div className="flex justify-between items-start mb-4">
              <div className={`p-2.5 rounded-xl ${stat.bg} ${stat.color} transition-colors`}>
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
            <div>
              <p className="text-3xl font-black text-emerald-950 mb-1 tracking-tight">{stat.value}</p>
              <p className="text-sm font-bold text-emerald-900/60 uppercase tracking-wide">{stat.name}</p>
            </div>
          </div>
        ))}
        </div>
      </div>

      {/* Funnel Velocity Metrics */}
      {velocity && (
        <div className="glass-card p-6 border-emerald-200/50 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <TrendingUp className="w-24 h-24 text-emerald-600" />
          </div>
          <h3 className="text-lg font-extrabold text-emerald-950 mb-4 flex items-center">
            <TrendingUp className="w-5 h-5 mr-2 text-emerald-600" />
            Funnel Velocity
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div>
              <p className="text-sm font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Time in Draft</p>
              <div className="flex items-end">
                <span className="text-2xl font-black text-emerald-950">{velocity.avg_days_in_draft}</span>
                <span className="text-sm font-semibold text-emerald-900/60 ml-1 mb-1">days avg</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Sent to Interview</p>
              <div className="flex items-end">
                <span className="text-2xl font-black text-emerald-950">{velocity.avg_days_to_interview}</span>
                <span className="text-sm font-semibold text-emerald-900/60 ml-1 mb-1">days avg</span>
              </div>
            </div>
            <div>
              <p className="text-sm font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Interview to Offer</p>
              <div className="flex items-end">
                <span className="text-2xl font-black text-emerald-950">{velocity.avg_days_to_offer}</span>
                <span className="text-sm font-semibold text-emerald-900/60 ml-1 mb-1">days avg</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Communication & AI Metrics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Communication Metrics */}
        {data?.communication && (
          <div className="glass-card p-6 border-emerald-200/50 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Mail className="w-20 h-20 text-emerald-600" />
            </div>
            <h3 className="text-lg font-extrabold text-emerald-950 mb-4 flex items-center">
              <Mail className="w-5 h-5 mr-2 text-emerald-600" />
              Communication Metrics
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Emails Sent</p>
                <span className="text-2xl font-black text-emerald-950">{data.communication.emails_sent}</span>
              </div>
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Delivered</p>
                <span className="text-2xl font-black text-emerald-950">{data.communication.emails_delivered}</span>
              </div>
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Reply Rate</p>
                <span className="text-2xl font-black text-emerald-950">{data.communication.reply_rate}%</span>
              </div>
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Replies</p>
                <span className="text-2xl font-black text-emerald-950">{data.communication.replies_received}</span>
              </div>
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Failed</p>
                <span className="text-2xl font-black text-rose-600">{data.communication.emails_failed}</span>
              </div>
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Follow-ups</p>
                <span className="text-2xl font-black text-amber-600">{data.communication.pending_followups}</span>
              </div>
            </div>
          </div>
        )}

        {/* AI Usage Metrics */}
        {data?.ai_metrics && (
          <div className="glass-card p-6 border-emerald-200/50 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Zap className="w-20 h-20 text-emerald-600" />
            </div>
            <h3 className="text-lg font-extrabold text-emerald-950 mb-4 flex items-center">
              <Zap className="w-5 h-5 mr-2 text-emerald-600" />
              AI Usage
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Total Generations</p>
                <span className="text-2xl font-black text-emerald-950">{data.ai_metrics.total_generations}</span>
              </div>
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Tokens Used</p>
                <span className="text-2xl font-black text-emerald-950">{data.ai_metrics.total_tokens_used.toLocaleString()}</span>
              </div>
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Resume AI</p>
                <span className="text-2xl font-black text-emerald-950">{data.ai_metrics.resume_generations}</span>
              </div>
              <div>
                <p className="text-xs font-bold text-emerald-900/60 uppercase tracking-wide mb-1">Email AI</p>
                <span className="text-2xl font-black text-emerald-950">{data.ai_metrics.email_generations}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Pipeline Timeline & Activity */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Pipeline Timeline */}
        <div className="glass-panel p-6 lg:col-span-2">
          <div className="flex justify-between items-center mb-8">
            <h3 className="text-base font-extrabold text-emerald-950 flex items-center">
              <Sparkles className="w-4 h-4 mr-2 text-emerald-600" />
              Candidate Funnel Timeline
            </h3>
            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
              Live Aggregate
            </span>
          </div>

          <div className="relative flex items-center justify-between w-full mt-4 pb-4">
            <div className="absolute top-1/2 left-0 right-0 h-1 bg-emerald-100/80 -translate-y-1/2 z-0 rounded-full" />
            
            {[
              { label: 'Drafts', value: data?.pipeline.draft ?? 0, color: 'bg-slate-400', active: true },
              { label: 'Ready', value: data?.pipeline.ready ?? 0, color: 'bg-emerald-600', active: true },
              { label: 'Sent', value: data?.pipeline.sent ?? 0, color: 'bg-teal-600', active: true },
              { label: 'Interviews', value: data?.pipeline.interview ?? 0, color: 'bg-emerald-700', active: true },
              { label: 'Offers', value: data?.pipeline.offer ?? 0, color: 'bg-teal-700', active: true },
            ].map((item) => (
              <div key={item.label} className="relative z-10 flex flex-col items-center group cursor-pointer w-20">
                <div className="flex flex-col items-center justify-center mb-3">
                  <span className="text-xl font-extrabold text-emerald-950 mb-1 group-hover:text-emerald-600 transition-colors">{item.value}</span>
                </div>
                <div 
                  className={`w-5 h-5 rounded-full border-2 border-white ring-4 transition-all duration-300 ${
                    item.active ? item.color + ' ring-emerald-100' : 'bg-slate-200 ring-transparent'
                  } group-hover:scale-125 shadow-sm`}
                />
                <span className="text-xs font-bold mt-3 text-center text-emerald-950">
                  {item.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Live Activity Stream — Real Notifications */}
        <div className="glass-panel p-6 relative overflow-hidden lg:col-span-1">
          <h3 className="text-base font-extrabold text-emerald-950 mb-6 flex items-center">
            <Bell className="w-4 h-4 mr-2 text-emerald-600" />
            Agent Updates
          </h3>
          
          <div className="space-y-4">
            {notifications.length > 0 ? (
              notifications.map((notif, i) => (
                <div key={notif.id} className={`flex space-x-3 p-2.5 rounded-xl ${i % 2 === 0 ? 'bg-emerald-50/60 border border-emerald-100' : 'bg-teal-50/60 border border-teal-100'}`}>
                  <div className={`w-2.5 h-2.5 rounded-full ${notif.is_read ? 'bg-slate-300' : 'bg-emerald-600 animate-ping'} mt-1.5 flex-shrink-0`} />
                  <div>
                    <p className="text-xs font-bold text-emerald-950">{notif.title}</p>
                    <p className="text-[10px] text-emerald-800/60 font-medium mt-0.5">{formatTimeAgo(notif.created_at)}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <Bell className="w-8 h-8 text-emerald-200 mx-auto mb-3" />
                <p className="text-xs font-bold text-emerald-900/50">No recent activity</p>
                <p className="text-[10px] text-emerald-800/40 mt-1">Updates will appear here as you use the platform.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
