'use client';

import { useState, useEffect } from 'react';
import { User, Loader2, Save, Link as LinkIcon, MapPin, Phone, Github, FileText, AlertTriangle, Trash2, Mail, CheckCircle2, ShieldCheck, HelpCircle, RefreshCw } from 'lucide-react';
import { fetchApi } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

interface EmailConfig {
  id?: string;
  provider_type: string;
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password?: string;
  display_name?: string;
  is_verified?: boolean;
}

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Delete account state
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Email disconnect modal state
  const [isDisconnectModalOpen, setIsDisconnectModalOpen] = useState(false);

  // Profile form state
  const [formData, setFormData] = useState({
    full_name: '',
    phone: '',
    location: '',
    linkedin_url: '',
    github_url: '',
    portfolio_url: '',
    bio: ''
  });

  // Email Config State
  const [emailConfig, setEmailConfig] = useState<EmailConfig>({
    provider_type: 'SMTP',
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    display_name: '',
    is_verified: false
  });
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailSaving, setEmailSaving] = useState(false);
  const [emailTesting, setEmailTesting] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [emailSuccess, setEmailSuccess] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [providerPreset, setProviderPreset] = useState<'gmail' | 'outlook' | 'custom'>('gmail');

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const profile = await fetchApi('/users/me');
        setFormData({
          full_name: profile.full_name || '',
          phone: profile.phone || '',
          location: profile.location || '',
          linkedin_url: profile.linkedin_url || '',
          github_url: profile.github_url || '',
          portfolio_url: profile.portfolio_url || '',
          bio: profile.bio || ''
        });
      } catch (err) {
        console.error('Failed to load profile:', err);
      }
    };

    const loadEmailConfig = async () => {
      setEmailLoading(true);
      try {
        const config = await fetchApi('/users/me/email-config');
        if (config) {
          setEmailConfig({
            ...config,
            smtp_password: '' // Keep password input clean for edit
          });
          if (config.smtp_host.includes('gmail')) setProviderPreset('gmail');
          else if (config.smtp_host.includes('outlook') || config.smtp_host.includes('office365')) setProviderPreset('outlook');
          else setProviderPreset('custom');
        }
      } catch (err) {
        console.error('No email config found or failed to load:', err);
      } finally {
        setEmailLoading(false);
      }
    };

    if (user) {
      loadProfile();
      loadEmailConfig();
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      // Convert empty strings to null for optional fields
      const cleanData = {
        ...formData,
        phone: formData.phone?.trim() || null,
        location: formData.location?.trim() || null,
        linkedin_url: formData.linkedin_url?.trim() || null,
        github_url: formData.github_url?.trim() || null,
        portfolio_url: formData.portfolio_url?.trim() || null,
        bio: formData.bio?.trim() || null,
      };
      await fetchApi('/users/me', {
        method: 'PATCH',
        body: JSON.stringify(cleanData)
      });
      setSuccess('Profile updated successfully!');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      console.error('Failed to update profile:', err);
      setError(err.message || 'Failed to update profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (preset: 'gmail' | 'outlook' | 'custom') => {
    setProviderPreset(preset);
    setTestResult(null);
    if (preset === 'gmail') {
      setEmailConfig(prev => ({ ...prev, provider_type: 'GMAIL_OAUTH', smtp_host: 'smtp.gmail.com', smtp_port: 587 }));
    } else if (preset === 'outlook') {
      setEmailConfig(prev => ({ ...prev, provider_type: 'OUTLOOK_OAUTH', smtp_host: 'smtp.office365.com', smtp_port: 587 }));
    } else {
      setEmailConfig(prev => ({ ...prev, provider_type: 'SMTP' }));
    }
  };

  const handleSaveEmailConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailConfig.smtp_username || !emailConfig.smtp_password) {
      setEmailError('Please enter both your email address and App Password.');
      return;
    }
    setEmailSaving(true);
    setEmailError(null);
    setEmailSuccess(null);
    setTestResult(null);
    try {
      const pType = providerPreset === 'gmail' ? 'GMAIL_OAUTH' : providerPreset === 'outlook' ? 'OUTLOOK_OAUTH' : 'SMTP';
      const updated = await fetchApi('/users/me/email-config', {
        method: 'POST',
        body: JSON.stringify({
          provider_type: pType,
          smtp_host: emailConfig.smtp_host,
          smtp_port: Number(emailConfig.smtp_port),
          smtp_username: emailConfig.smtp_username,
          smtp_password: emailConfig.smtp_password,
          display_name: emailConfig.display_name || formData.full_name || undefined
        })
      });
      setEmailConfig(prev => ({ ...prev, ...updated, smtp_password: '' }));
      setEmailSuccess('Email configuration saved successfully! Credentials are encrypted at rest.');
      setTimeout(() => setEmailSuccess(null), 4000);
    } catch (err: any) {
      console.error('Failed to save email config:', err);
      setEmailError(err.message || 'Failed to save email config. Check your inputs.');
    } finally {
      setEmailSaving(false);
    }
  };

  const handleTestEmailConfig = async () => {
    setEmailTesting(true);
    setTestResult(null);
    setEmailError(null);
    try {
      const result = await fetchApi('/users/me/email-config/test', {
        method: 'POST'
      });
      setTestResult(result);
      if (result.success) {
        setEmailConfig(prev => ({ ...prev, is_verified: true }));
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || 'Connection test failed. Check your email configuration.'
      });
    } finally {
      setEmailTesting(false);
    }
  };

  const handleDisconnectEmail = async () => {
    try {
      await fetchApi('/users/me/email-config', { method: 'DELETE' });
      setEmailConfig({
        provider_type: 'SMTP',
        smtp_host: 'smtp.gmail.com',
        smtp_port: 587,
        smtp_username: '',
        smtp_password: '',
        display_name: '',
        is_verified: false
      });
      setEmailSuccess('Email provider disconnected.');
      setTestResult(null);
      setIsDisconnectModalOpen(false);
      setTimeout(() => setEmailSuccess(null), 3000);
    } catch (err: any) {
      setEmailError(err.message || 'Failed to disconnect email provider');
      setIsDisconnectModalOpen(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleteLoading(true);
    try {
      await fetchApi('/users/me', { method: 'DELETE' });
      logout();
    } catch (err: any) {
      console.error('Failed to delete account:', err);
      alert(err.message || 'Failed to delete account');
      setDeleteLoading(false);
      setIsDeleteModalOpen(false);
    }
  };

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out max-w-4xl pb-12">
      <div>
        <h2 className="text-3xl font-extrabold tracking-tight text-emerald-950 mb-2">Profile & Email Settings</h2>
        <p className="text-emerald-900/70 font-medium">Manage your personal details and connect your email provider for outreach.</p>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-600 p-4 rounded-xl text-sm font-semibold">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-4 rounded-xl text-sm font-semibold">
          {success}
        </div>
      )}

      {/* Profile Form Card */}
      <div className="rounded-2xl bg-white border border-emerald-100 p-8 shadow-sm">
        <h3 className="text-xl font-bold text-emerald-950 mb-6 flex items-center">
          <User className="w-5 h-5 mr-2 text-emerald-600" />
          Personal Profile
        </h3>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Full Name</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-4 w-4 text-emerald-600/50" />
                </div>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                  className="block w-full pl-10 pr-3 py-2.5 border border-emerald-200/80 rounded-xl bg-white/80 text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Location</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <MapPin className="h-4 w-4 text-emerald-600/50" />
                </div>
                <input
                  type="text"
                  value={formData.location}
                  onChange={e => setFormData({ ...formData, location: e.target.value })}
                  className="block w-full pl-10 pr-3 py-2.5 border border-emerald-200/80 rounded-xl bg-white/80 text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Phone</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Phone className="h-4 w-4 text-emerald-600/50" />
                </div>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={e => setFormData({ ...formData, phone: e.target.value })}
                  className="block w-full pl-10 pr-3 py-2.5 border border-emerald-200/80 rounded-xl bg-white/80 text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">LinkedIn URL</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <LinkIcon className="h-4 w-4 text-emerald-600/50" />
                </div>
                <input
                  type="url"
                  value={formData.linkedin_url}
                  onChange={e => setFormData({ ...formData, linkedin_url: e.target.value })}
                  className="block w-full pl-10 pr-3 py-2.5 border border-emerald-200/80 rounded-xl bg-white/80 text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">GitHub URL</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Github className="h-4 w-4 text-emerald-600/50" />
                </div>
                <input
                  type="url"
                  value={formData.github_url}
                  onChange={e => setFormData({ ...formData, github_url: e.target.value })}
                  className="block w-full pl-10 pr-3 py-2.5 border border-emerald-200/80 rounded-xl bg-white/80 text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Bio Summary</label>
              <div className="relative">
                <div className="absolute top-3 left-3 pointer-events-none">
                  <FileText className="h-4 w-4 text-emerald-600/50" />
                </div>
                <textarea
                  rows={3}
                  value={formData.bio}
                  onChange={e => setFormData({ ...formData, bio: e.target.value })}
                  className="block w-full pl-10 pr-3 py-2.5 border border-emerald-200/80 rounded-xl bg-white/80 text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                  placeholder="A brief professional summary..."
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-emerald-100">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary py-2.5 px-6 text-xs flex items-center"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
              Save Profile
            </button>
          </div>
        </form>
      </div>

      {/* ── EMAIL PROVIDER CONNECTION CARD (NEW) ───────────────────────── */}
      <div className="rounded-2xl bg-white border border-emerald-100 p-8 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h3 className="text-xl font-bold text-emerald-950 flex items-center">
              <Mail className="w-5 h-5 mr-2 text-emerald-600" />
              Email Outreach Connection
            </h3>
            <p className="text-xs text-emerald-900/70 mt-1">
              Connect your personal Gmail App Password or SMTP server so cold emails are sent directly from your email address.
            </p>
          </div>

          {emailConfig.id && (
            <div className="flex items-center space-x-2">
              {emailConfig.is_verified ? (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-500" />
                  Verified
                </span>
              ) : (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
                  Connected (Unverified)
                </span>
              )}
            </div>
          )}
        </div>

        {emailError && (
          <div className="bg-rose-50 border border-rose-200 text-rose-600 p-4 rounded-xl text-xs font-semibold">
            {emailError}
          </div>
        )}

        {emailSuccess && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-4 rounded-xl text-xs font-semibold">
            {emailSuccess}
          </div>
        )}

        {/* Preset Tabs */}
        <div>
          <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Select Provider Preset</label>
          <div className="grid grid-cols-3 gap-3 max-w-md">
            <button
              type="button"
              onClick={() => handleSelectPreset('gmail')}
              className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all flex items-center justify-center ${providerPreset === 'gmail'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300 ring-2 ring-emerald-500/20'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                }`}
            >
              🌐 Google Gmail
            </button>
            <button
              type="button"
              onClick={() => handleSelectPreset('outlook')}
              className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all flex items-center justify-center ${providerPreset === 'outlook'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300 ring-2 ring-emerald-500/20'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                }`}
            >
              📧 Outlook
            </button>
            <button
              type="button"
              onClick={() => handleSelectPreset('custom')}
              className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all flex items-center justify-center ${providerPreset === 'custom'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300 ring-2 ring-emerald-500/20'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                }`}
            >
              ✉️ Custom SMTP
            </button>
          </div>
        </div>

        {providerPreset === 'gmail' && (
          <div className="space-y-4">
            {/* Google OAuth — Primary Option */}
            {emailConfig.provider_type !== 'GMAIL_OAUTH' || !emailConfig.is_verified ? (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/80 p-5 rounded-xl space-y-3">
                <div className="flex items-start space-x-3">
                  <div className="p-2 bg-blue-100 rounded-xl flex-shrink-0 mt-0.5">
                    <svg className="w-5 h-5 text-blue-600" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-bold text-sm text-blue-900">Connect with Google (Recommended)</h4>
                    <p className="text-xs text-blue-800/80 mt-0.5 leading-relaxed">
                      One-click setup — no App Password needed. Securely connects your Gmail account via Google OAuth to send outreach emails.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const token = localStorage.getItem('access_token');
                    window.location.href = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/google/authorize?access_token=${token}`;
                  }}
                  className="w-full py-3 bg-white hover:bg-blue-50 text-blue-700 border-2 border-blue-300 rounded-xl text-sm font-bold transition-all flex items-center justify-center shadow-sm hover:shadow-md"
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
                  Connect with Google
                </button>
              </div>
            ) : (
              <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-xl flex items-center space-x-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                <div className="flex-1">
                  <h4 className="font-bold text-sm text-emerald-900">Google OAuth Connected ✅</h4>
                  <p className="text-xs text-emerald-800/70 mt-0.5">
                    Your Gmail account ({emailConfig.smtp_username}) is connected via Google OAuth. Emails are sent securely without an App Password.
                  </p>
                </div>
              </div>
            )}

            {/* App Password Fallback */}
            <div className="bg-slate-50/70 border border-slate-200/80 p-4 rounded-xl flex items-start space-x-3 text-xs text-slate-700">
              <HelpCircle className="w-5 h-5 text-slate-500 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-bold">Alternative: Use a Google App Password</p>
                <ol className="list-decimal list-inside space-y-0.5 text-slate-600">
                  <li>Go to your Google Account (myaccount.google.com) &rarr; <strong>Security</strong>.</li>
                  <li>Ensure <strong>2-Step Verification</strong> is ON. Search for <strong>&quot;App Passwords&quot;</strong>.</li>
                  <li>Create an App Password named &quot;Ascendra&quot; and copy the 16-character code into the field below.</li>
                </ol>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSaveEmailConfig} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Display Name (From Header)</label>
              <input
                type="text"
                placeholder="e.g., Your Name"
                value={emailConfig.display_name || ''}
                onChange={e => setEmailConfig({ ...emailConfig, display_name: e.target.value })}
                className="block w-full px-3 py-2.5 border border-emerald-200/80 rounded-xl bg-white text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Email Address / Username</label>
              <input
                type="email"
                required
                placeholder="e.g., yourname@provider.com"
                value={emailConfig.smtp_username}
                onChange={e => setEmailConfig({ ...emailConfig, smtp_username: e.target.value })}
                className="block w-full px-3 py-2.5 border border-emerald-200/80 rounded-xl bg-white text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">
                App Password / Secret Key 🔒
              </label>
              <input
                type="password"
                required={!emailConfig.id}
                placeholder={emailConfig.id ? "•••••••••••••••• (Leave blank to keep existing)" : "Paste 16-char Google App Password"}
                value={emailConfig.smtp_password || ''}
                onChange={e => setEmailConfig({ ...emailConfig, smtp_password: e.target.value })}
                className="block w-full px-3 py-2.5 border border-emerald-200/80 rounded-xl bg-white text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
              />
              <p className="text-[10px] text-emerald-900/60 mt-1 flex items-center">
                <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                Passwords are encrypted at rest with AES-256 and never returned to browser logs.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">SMTP Host</label>
                <input
                  type="text"
                  required
                  value={emailConfig.smtp_host}
                  onChange={e => setEmailConfig({ ...emailConfig, smtp_host: e.target.value })}
                  className="block w-full px-3 py-2.5 border border-emerald-200/80 rounded-xl bg-slate-50 text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Port</label>
                <input
                  type="number"
                  required
                  value={emailConfig.smtp_port}
                  onChange={e => setEmailConfig({ ...emailConfig, smtp_port: Number(e.target.value) })}
                  className="block w-full px-3 py-2.5 border border-emerald-200/80 rounded-xl bg-slate-50 text-slate-800 text-sm focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>
            </div>
          </div>

          {/* Test Connection Banner */}
          {testResult && (
            <div className={`p-4 rounded-xl border text-xs font-bold flex items-center justify-between ${testResult.success
              ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
              : 'bg-rose-50 border-rose-200 text-rose-600'
              }`}>
              <span>{testResult.success ? '✅ ' : '❌ '}{testResult.message}</span>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between pt-4 border-t border-emerald-100 gap-3">
            <div className="flex items-center space-x-3">
              {emailConfig.id && (
                <button
                  type="button"
                  onClick={handleTestEmailConfig}
                  disabled={emailTesting}
                  className="py-2.5 px-4 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-bold transition-all flex items-center"
                >
                  {emailTesting ? <Loader2 className="w-4 h-4 animate-spin mr-1.5" /> : <RefreshCw className="w-4 h-4 mr-1.5" />}
                  Test Connection
                </button>
              )}
              {emailConfig.id && (
                <button
                  type="button"
                  onClick={() => setIsDisconnectModalOpen(true)}
                  className="py-2.5 px-4 text-rose-600 hover:bg-rose-50 rounded-xl text-xs font-bold transition-colors"
                >
                  Disconnect
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={emailSaving}
              className="btn-primary py-2.5 px-6 text-xs flex items-center"
            >
              {emailSaving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
              Save Email Credentials
            </button>
          </div>
        </form>
      </div>

      {/* Danger Zone Card */}
      <div className="rounded-2xl bg-red-50 border border-red-200 p-8 shadow-sm">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <AlertTriangle className="h-6 w-6 text-red-500" />
          </div>
          <div className="ml-4">
            <h3 className="text-lg font-medium text-slate-800 mb-1">Danger Zone</h3>
            <p className="text-sm text-slate-600 mb-6">
              Permanently delete your account and all of your data, including jobs, resumes, and contacts. This action cannot be undone.
            </p>
            <button
              onClick={() => setIsDeleteModalOpen(true)}
              className="flex justify-center items-center py-2 px-4 border border-red-200 rounded-xl shadow-sm text-sm font-medium text-red-600 bg-white hover:bg-red-50 focus:outline-none transition-colors"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Account
            </button>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-red-500" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Delete Account</h3>
              <p className="text-sm text-slate-600 mb-6">
                Are you absolutely sure you want to delete your account? This action cannot be undone and will permanently erase all your data.
              </p>

              <div className="flex space-x-3">
                <button
                  onClick={() => setIsDeleteModalOpen(false)}
                  disabled={deleteLoading}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 focus:outline-none transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteAccount}
                  disabled={deleteLoading}
                  className="flex-1 flex justify-center items-center py-2.5 px-4 border border-transparent rounded-xl text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none transition-colors disabled:opacity-50"
                >
                  {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Yes, Delete My Account
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Disconnect Email Modal */}
      {isDisconnectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-amber-500" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Disconnect Email Provider?</h3>
              <p className="text-sm text-slate-600 mb-6">
                This will remove your SMTP configuration. Outreach emails will revert to the system default sending method.
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => setIsDisconnectModalOpen(false)}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDisconnectEmail}
                  className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-xl text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 transition-colors"
                >
                  Disconnect
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
