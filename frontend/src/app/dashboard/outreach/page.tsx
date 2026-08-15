'use client';

import { useState, useEffect } from 'react';
import { Send, Loader2, Search, User, Mail, Link as LinkIcon, Building2, Wand2, X, Sparkles, AlertTriangle, Settings, Edit3, RotateCcw, Paperclip, Clock, CalendarClock, XCircle } from 'lucide-react';
import { fetchApi } from '@/lib/api';
import LinkifiedText from '@/components/common/LinkifiedText';
import Link from 'next/link';

interface Contact {
  id: string;
  full_name: string;
  job_title: string;
  email: string;
  linkedin_url: string;
  created_at: string;
}

interface Application {
  id: string;
  job_id: string;
  job_title_snapshot: string;
  company_name_snapshot: string;
  status: string;
  created_at: string;
}

export default function OutreachPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'applications' | 'contacts' | 'followups' | 'scheduled'>('applications');

  // Email credentials check: 'loading' | 'configured' | 'unverified' | 'none'
  const [emailConfigStatus, setEmailConfigStatus] = useState<'loading' | 'configured' | 'unverified' | 'none'>('loading');

  // AI Email Modal State
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [emailTone, setEmailTone] = useState('professional');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<{subject: string, body_text: string} | null>(null);
  const [isEdited, setIsEdited] = useState(false);

  // Resume picker state
  const [resumes, setResumes] = useState<any[]>([]);
  const [resumeVersions, setResumeVersions] = useState<any[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>('auto');

  // Company contacts for recipient picker
  const [companyContacts, setCompanyContacts] = useState<Contact[]>([]);

  // Discover Contacts Modal State
  const [isDiscoverModalOpen, setIsDiscoverModalOpen] = useState(false);
  const [discoverDomain, setDiscoverDomain] = useState('');
  const [discoverLoading, setDiscoverLoading] = useState(false);

  // Follow-up Modal State
  const [isFollowUpModalOpen, setIsFollowUpModalOpen] = useState(false);
  const [followUpConversationId, setFollowUpConversationId] = useState('');
  const [followUpNumber, setFollowUpNumber] = useState(1);
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [followUpResult, setFollowUpResult] = useState<{subject: string, body_text: string, body_html?: string} | null>(null);
  const [followUpEdited, setFollowUpEdited] = useState(false);
  const [followUpRecipient, setFollowUpRecipient] = useState('');
  const [followUpSendSuccess, setFollowUpSendSuccess] = useState<string | null>(null);

  // Conversations list for follow-up tab
  const [conversations, setConversations] = useState<any[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);

  // Scheduled sending state
  const [showSchedulePicker, setShowSchedulePicker] = useState(false);
  const [scheduledDateTime, setScheduledDateTime] = useState('');
  const [scheduledMessages, setScheduledMessages] = useState<any[]>([]);
  const [scheduledMessagesLoading, setScheduledMessagesLoading] = useState(false);
  const [scheduleActionLoading, setScheduleActionLoading] = useState<string | null>(null);
  const [rescheduleId, setRescheduleId] = useState<string | null>(null);
  const [rescheduleDateTime, setRescheduleDateTime] = useState('');

  // Follow-up schedule picker state
  const [showFollowUpSchedulePicker, setShowFollowUpSchedulePicker] = useState(false);
  const [followUpScheduledDateTime, setFollowUpScheduledDateTime] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setError(null);
      const [appData, contactData] = await Promise.all([
        fetchApi('/applications'),
        fetchApi('/contacts')
      ]);
      const appItems = appData.items || appData || [];
      const contactItems = contactData.items || contactData || [];

      setApplications(appItems);
      setContacts(contactItems);
    } catch (err: any) {
      console.error('Failed to load outreach data:', err);
      setError('Could not load outreach data. Please check your connection and try again.');
      setApplications([]);
      setContacts([]);
    } finally {
      setLoading(false);
    }
  };

  // Check if user has configured email credentials
  useEffect(() => {
    fetchApi('/users/me/email-config')
      .then((config) => {
        if (config && (config.smtp_host || config.provider_type === 'GMAIL_OAUTH')) {
          setEmailConfigStatus(config.is_verified ? 'configured' : 'unverified');
        } else {
          setEmailConfigStatus('none');
        }
      })
      .catch(() => {
        // Don't overwrite state on transient API errors — keep previous state
        setEmailConfigStatus((prev) => prev === 'loading' ? 'none' : prev);
      });
  }, []);

  const [recipientEmail, setRecipientEmail] = useState('');
  const [sendSuccess, setSendSuccess] = useState<string | null>(null);

  const getDomainFromCompanyName = (companyName: string) => {
    if (!companyName) return '';
    const clean = companyName.toLowerCase().replace(/[^a-z0-9]/g, '');
    return clean ? `${clean}.com` : '';
  };

  const openEmailModal = async (app: Application) => {
    setSelectedApp(app);
    setAiResult(null);
    setSendSuccess(null);
    setSelectedResumeId('auto');
    setShowSchedulePicker(false);
    setScheduledDateTime('');
    
    // Find contacts whose email domain matches the company name
    const companyName = (app.company_name_snapshot || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    const matching = contacts.filter(c => {
      if (!c.email) return false;
      const emailDomain = c.email.split('@')[1]?.toLowerCase() || '';
      const emailLocal = c.email.split('@')[0]?.toLowerCase() || '';
      // Match if company name appears in the email domain OR in the full email
      return emailDomain.includes(companyName.substring(0, Math.min(companyName.length, 8)))
        || c.email.toLowerCase().includes(companyName);
    });
    setCompanyContacts(matching);

    // Auto-select first matching contact, or leave empty
    if (matching.length > 0) {
      setRecipientEmail(matching[0].email);
    } else {
      setRecipientEmail('');
    }

    setIsEmailModalOpen(true);

    // Fetch resumes and versions for attachment picker
    try {
      const [resumeData, versionData] = await Promise.all([
        fetchApi('/resumes'),
        fetchApi('/resume-versions'),
      ]);
      setResumes(Array.isArray(resumeData) ? resumeData : resumeData.items || []);
      setResumeVersions(Array.isArray(versionData) ? versionData : versionData.items || []);
    } catch {
      setResumes([]);
      setResumeVersions([]);
    }
  };

  const handleSendEmail = async () => {
    if (!selectedApp || !aiResult) return;
    if (!recipientEmail.trim()) {
      setError('Please enter a recipient email address (e.g. recruiter@company.com).');
      return;
    }
    setAiLoading(true);
    setError(null);
    setSendSuccess(null);
    try {
      // 1. Create Draft (include body_html so email clients render content)
      const htmlBody = aiResult.body_text
        .split('\n')
        .map((line: string) => line.trim() === '' ? '<br/>' : `<p>${line}</p>`)
        .join('\n');

      const draftBody: any = {
          application_id: selectedApp.id,
          to_email: recipientEmail.trim(),
          subject: aiResult.subject,
          body_text: aiResult.body_text,
          body_html: htmlBody,
      };
      if (selectedResumeId && selectedResumeId !== 'none' && selectedResumeId !== 'auto') {
        draftBody.resume_version_id = selectedResumeId;
      }
      const draftRes = await fetchApi('/email/draft', {
        method: 'POST',
        body: JSON.stringify(draftBody)
      });
      const messageId = draftRes.message?.id || draftRes.id;

      // 2. Approve Draft
      await fetchApi(`/email/${messageId}/approve`, {
        method: 'POST'
      });

      // 3. Queue Send
      await fetchApi(`/email/${messageId}/send`, {
        method: 'POST'
      });

      setSendSuccess('Email queued for background delivery via your active email provider!');
      setTimeout(() => {
        setIsEmailModalOpen(false);
        setSendSuccess(null);
      }, 2500);
    } catch (err: any) {
      console.error('Failed to send email:', err);
      setError(err.message || 'Failed to send email. Check your SMTP settings in Profile.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleGenerateEmail = async () => {
    if (!selectedApp) return;
    setAiLoading(true);
    setError(null);
    try {
      const res = await fetchApi('/ai/email/generate', {
        method: 'POST',
        body: JSON.stringify({
          application_id: selectedApp.id,
          tone: emailTone,
        })
      });
      const data = res.data || res;
      setAiResult({
        subject: data.subject || `Re: ${selectedApp.job_title_snapshot} opportunity`,
        body_text: data.body_text || data.body || '',
      });
    } catch (err: any) {
      console.error('Failed to generate email:', err);
      setError(err.message || 'AI email generation failed. Please try again.');
    } finally {
      setAiLoading(false);
    }
  };

  const openDiscoverModal = (app: Application) => {
    setSelectedApp(app);
    const defaultDomain = getDomainFromCompanyName(app.company_name_snapshot || '');
    setDiscoverDomain(defaultDomain);
    setIsDiscoverModalOpen(true);
  };

  const handleDiscoverContacts = async () => {
    if (!selectedApp || !discoverDomain.trim()) return;
    setDiscoverLoading(true);
    setError(null);
    try {
      const results = await fetchApi(`/contacts/discover?company_id=${selectedApp.job_id}&company_domain=${encodeURIComponent(discoverDomain.trim())}`, {
        method: 'POST',
      });
      const newContacts = Array.isArray(results) ? results : results.items || [];
      if (newContacts.length > 0) {
        setContacts(prev => [...newContacts, ...prev]);
        setIsDiscoverModalOpen(false);
        setActiveTab('contacts');
      } else {
        setError('No contacts found for this domain. Try a different domain or add contacts manually.');
      }
    } catch (err: any) {
      console.error('Failed to discover contacts:', err);
      setError(err.message || 'Failed to discover contacts.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setDiscoverLoading(false);
    }
  };

  // ── Follow-up Handlers ────────────────────────────────

  const loadConversations = async () => {
    setConversationsLoading(true);
    try {
      const data = await fetchApi('/conversations');
      setConversations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load conversations:', err);
      setConversations([]);
    } finally {
      setConversationsLoading(false);
    }
  };

  // ── Scheduled Sending Handlers ────────────────────────────

  const getMinScheduleDateTime = () => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 5);
    // datetime-local input expects local time format, NOT UTC
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  const loadScheduledMessages = async () => {
    setScheduledMessagesLoading(true);
    try {
      const convos = await fetchApi('/conversations');
      const convoList = Array.isArray(convos) ? convos : [];
      const allScheduled: any[] = [];
      for (const conv of convoList) {
        try {
          const messages = await fetchApi(`/conversations/${conv.id}/messages`);
          const msgList = Array.isArray(messages) ? messages : [];
          for (const msg of msgList) {
            if (msg.status === 'SCHEDULED') {
              allScheduled.push({ ...msg, conversation_subject: conv.subject });
            }
          }
        } catch { /* skip */ }
      }
      setScheduledMessages(allScheduled);
    } catch (err) {
      console.error('Failed to load scheduled messages:', err);
      setScheduledMessages([]);
    } finally {
      setScheduledMessagesLoading(false);
    }
  };

  const handleScheduleEmail = async () => {
    if (!selectedApp || !aiResult) return;
    if (!recipientEmail.trim()) {
      setError('Please enter a recipient email address.');
      return;
    }
    if (!scheduledDateTime) {
      setError('Please select a date and time for scheduling.');
      return;
    }
    setAiLoading(true);
    setError(null);
    setSendSuccess(null);
    try {
      const htmlBody = aiResult.body_text
        .split('\n')
        .map((line: string) => line.trim() === '' ? '<br/>' : `<p>${line}</p>`)
        .join('\n');

      const draftBody: any = {
        application_id: selectedApp.id,
        to_email: recipientEmail.trim(),
        subject: aiResult.subject,
        body_text: aiResult.body_text,
        body_html: htmlBody,
      };
      if (selectedResumeId && selectedResumeId !== 'none' && selectedResumeId !== 'auto') {
        draftBody.resume_version_id = selectedResumeId;
      }

      // 1. Create Draft
      const draftRes = await fetchApi('/email/draft', {
        method: 'POST',
        body: JSON.stringify(draftBody)
      });
      const messageId = draftRes.message?.id || draftRes.id;

      // 2. Approve Draft
      await fetchApi(`/email/${messageId}/approve`, { method: 'POST' });

      // 3. Schedule
      await fetchApi(`/email/${messageId}/schedule`, {
        method: 'POST',
        body: JSON.stringify({ scheduled_at: new Date(scheduledDateTime).toISOString() })
      });

      const formattedTime = new Date(scheduledDateTime).toLocaleString();
      setSendSuccess(`Email scheduled for ${formattedTime}! ⏰`);
      setShowSchedulePicker(false);
      setScheduledDateTime('');
      setTimeout(() => {
        setIsEmailModalOpen(false);
        setSendSuccess(null);
      }, 2500);
    } catch (err: any) {
      console.error('Failed to schedule email:', err);
      setError(err.message || 'Failed to schedule email.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleScheduleFollowUp = async () => {
    if (!followUpResult || !followUpRecipient) return;
    if (!followUpScheduledDateTime) {
      setError('Please select a date and time for scheduling.');
      return;
    }
    setFollowUpLoading(true);
    setError(null);
    try {
      const conv = conversations.find((c: any) => c.id === followUpConversationId);
      const appId = conv?.application_id;
      if (!appId) throw new Error('No application linked to this conversation.');

      const htmlBody = followUpResult.body_html || ('<p>' + followUpResult.body_text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br/>') + '</p>');

      // 1. Create Draft
      const draftRes = await fetchApi('/email/draft', {
        method: 'POST',
        body: JSON.stringify({
          application_id: appId,
          to_email: followUpRecipient.trim(),
          subject: followUpResult.subject,
          body_text: followUpResult.body_text,
          body_html: htmlBody,
        })
      });
      const messageId = draftRes.message?.id || draftRes.id;

      // 2. Approve
      await fetchApi(`/email/${messageId}/approve`, { method: 'POST' });

      // 3. Schedule
      await fetchApi(`/email/${messageId}/schedule`, {
        method: 'POST',
        body: JSON.stringify({ scheduled_at: new Date(followUpScheduledDateTime).toISOString() })
      });

      const formattedTime = new Date(followUpScheduledDateTime).toLocaleString();
      setFollowUpSendSuccess(`Follow-up scheduled for ${formattedTime}! ⏰`);
      setShowFollowUpSchedulePicker(false);
      setFollowUpScheduledDateTime('');
      setTimeout(() => {
        setIsFollowUpModalOpen(false);
        setFollowUpSendSuccess(null);
        loadConversations();
      }, 2500);
    } catch (err: any) {
      console.error('Failed to schedule follow-up:', err);
      setError(err.message || 'Failed to schedule follow-up.');
    } finally {
      setFollowUpLoading(false);
    }
  };

  const formatScheduledTime = (isoString: string) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffMins = Math.round(diffMs / 60000);
    const diffHours = Math.round(diffMs / 3600000);
    const diffDays = Math.round(diffMs / 86400000);

    let relative = '';
    if (diffMins < 1) relative = 'any moment';
    else if (diffMins < 60) relative = `in ${diffMins}m`;
    else if (diffHours < 24) relative = `in ${diffHours}h`;
    else relative = `in ${diffDays}d`;

    return {
      absolute: date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }),
      relative,
    };
  };

  const openFollowUpModal = (conversationId: string, recipientEmail: string) => {
    setFollowUpConversationId(conversationId);
    setFollowUpRecipient(recipientEmail);
    setFollowUpNumber(1);
    setFollowUpResult(null);
    setFollowUpEdited(false);
    setFollowUpSendSuccess(null);
    setShowFollowUpSchedulePicker(false);
    setFollowUpScheduledDateTime('');
    setIsFollowUpModalOpen(true);
  };

  const handleGenerateFollowUp = async () => {
    if (!followUpConversationId) return;
    setFollowUpLoading(true);
    setError(null);
    try {
      const res = await fetchApi('/ai/email/followup', {
        method: 'POST',
        body: JSON.stringify({
          conversation_id: followUpConversationId,
          follow_up_number: followUpNumber,
          tone: 'professional',
        })
      });
      const data = res.data || res;
      setFollowUpResult({
        subject: data.subject || '',
        body_text: data.body_text || '',
        body_html: data.body_html || '',
      });
      setFollowUpEdited(false);
    } catch (err: any) {
      console.error('Failed to generate follow-up:', err);
      setError(err.message || 'Follow-up generation failed.');
    } finally {
      setFollowUpLoading(false);
    }
  };

  const handleSendFollowUp = async () => {
    if (!followUpResult || !followUpRecipient) return;
    setFollowUpLoading(true);
    try {
      // Find the application_id from the conversation
      const conv = conversations.find((c: any) => c.id === followUpConversationId);
      const appId = conv?.application_id;
      if (!appId) throw new Error('No application linked to this conversation.');

      const htmlBody = followUpResult.body_html || ('<p>' + followUpResult.body_text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br/>') + '</p>');

      // 1. Create Draft
      const draftRes = await fetchApi('/email/draft', {
        method: 'POST',
        body: JSON.stringify({
          application_id: appId,
          to_email: followUpRecipient.trim(),
          subject: followUpResult.subject,
          body_text: followUpResult.body_text,
          body_html: htmlBody,
        })
      });
      const messageId = draftRes.message?.id || draftRes.id;

      // 2. Approve
      await fetchApi(`/email/${messageId}/approve`, { method: 'POST' });

      // 3. Queue Send
      await fetchApi(`/email/${messageId}/send`, { method: 'POST' });

      setFollowUpSendSuccess('Follow-up email queued for delivery!');
      setTimeout(() => {
        setIsFollowUpModalOpen(false);
        setFollowUpSendSuccess(null);
        loadConversations(); // Refresh
      }, 2500);
    } catch (err: any) {
      console.error('Failed to send follow-up:', err);
      setError(err.message || 'Failed to send follow-up.');
    } finally {
      setFollowUpLoading(false);
    }
  };

  const filteredApps = applications.filter(a => 
    (a.job_title_snapshot || '').toLowerCase().includes(searchQuery.toLowerCase()) || 
    (a.company_name_snapshot || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredContacts = contacts.filter(c => 
    c.full_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    (c.job_title || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      {/* Informative Header Banner */}
      <div className="bg-gradient-to-r from-emerald-900/90 to-teal-900/90 text-white p-4 rounded-2xl shadow-md border border-emerald-700/50">
        <div className="flex items-start space-x-3">
          <div className="p-2 bg-emerald-500/20 rounded-xl mt-0.5">
            <Sparkles className="w-5 h-5 text-emerald-300" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-emerald-100">Recruiter Outreach & Contact Discovery</h3>
            <p className="text-xs text-emerald-200/80 mt-0.5 leading-relaxed">
              Supercharge your job application response rates. Click <strong>"AI Email"</strong> to generate tailored cold emails for hiring managers, or click <strong>"Find Contacts"</strong> to discover key recruiter email addresses at target company domains.
            </p>
          </div>
        </div>
      </div>

      {/* Email Credentials Warning Banner — only shows when truly unconfigured or unverified */}
      {emailConfigStatus === 'none' && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-start space-x-3 animate-in fade-in slide-in-from-top-2 duration-500">
          <div className="p-2 bg-amber-100 rounded-xl mt-0.5 flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
          </div>
          <div className="flex-1">
            <h4 className="font-bold text-sm text-amber-900">Email Credentials Not Configured</h4>
            <p className="text-xs text-amber-800/80 mt-0.5 leading-relaxed">
              Outreach emails cannot be sent until you configure your own email credentials (SMTP / App Password) or connect with Google OAuth.
              The application does <strong>not</strong> use a shared system email — your emails are sent from your own account for authenticity.
            </p>
          </div>
          <Link
            href="/dashboard/profile"
            className="flex-shrink-0 inline-flex items-center px-3.5 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold transition-colors shadow-sm"
          >
            <Settings className="w-3.5 h-3.5 mr-1.5" />
            Configure Email
          </Link>
        </div>
      )}
      {emailConfigStatus === 'unverified' && (
        <div className="bg-sky-50 border border-sky-200 rounded-2xl p-4 flex items-start space-x-3 animate-in fade-in slide-in-from-top-2 duration-500">
          <div className="p-2 bg-sky-100 rounded-xl mt-0.5 flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-sky-600" />
          </div>
          <div className="flex-1">
            <h4 className="font-bold text-sm text-sky-900">Email Not Verified</h4>
            <p className="text-xs text-sky-800/80 mt-0.5 leading-relaxed">
              Your email credentials are saved but not yet verified. Please send a test email from your profile to activate outreach.
            </p>
          </div>
          <Link
            href="/dashboard/profile"
            className="flex-shrink-0 inline-flex items-center px-3.5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-bold transition-colors shadow-sm"
          >
            <Settings className="w-3.5 h-3.5 mr-1.5" />
            Verify Now
          </Link>
        </div>
      )}

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-emerald-950 mb-1">Outreach & Network</h2>
          <p className="text-emerald-900/70 font-medium">Generate AI cold emails and track recruiter connections.</p>
        </div>
        
        <div className="relative w-full sm:w-64">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-emerald-600/50" />
          </div>
          <input
            type="text"
            placeholder="Search network..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="block w-full pl-10 pr-3 py-2 border border-emerald-200/80 rounded-xl bg-white/90 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-sm transition-all shadow-sm"
          />
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-600 p-4 rounded-xl text-sm font-semibold">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-emerald-100">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('applications')}
            className={`whitespace-nowrap pb-4 px-1 border-b-2 font-bold text-sm transition-colors ${
              activeTab === 'applications'
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-emerald-900/60 hover:text-emerald-950 hover:border-emerald-200'
            }`}
          >
            Applications ({applications.length})
          </button>
          <button
            onClick={() => setActiveTab('contacts')}
            className={`whitespace-nowrap pb-4 px-1 border-b-2 font-bold text-sm transition-colors ${
              activeTab === 'contacts'
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-emerald-900/60 hover:text-emerald-950 hover:border-emerald-200'
            }`}
          >
            Contacts ({contacts.length})
          </button>
          <button
            onClick={() => { setActiveTab('followups'); loadConversations(); }}
            className={`whitespace-nowrap pb-4 px-1 border-b-2 font-bold text-sm transition-colors ${
              activeTab === 'followups'
                ? 'border-emerald-600 text-emerald-700'
                : 'border-transparent text-emerald-900/60 hover:text-emerald-950 hover:border-emerald-200'
            }`}
          >
            Follow-ups
          </button>
          <button
            onClick={() => { setActiveTab('scheduled'); loadScheduledMessages(); }}
            className={`whitespace-nowrap pb-4 px-1 border-b-2 font-bold text-sm transition-colors ${
              activeTab === 'scheduled'
                ? 'border-violet-600 text-violet-700'
                : 'border-transparent text-emerald-900/60 hover:text-emerald-950 hover:border-emerald-200'
            }`}
          >
            <span className="flex items-center">
              <Clock className="w-3.5 h-3.5 mr-1.5" />
              Scheduled{scheduledMessages.length > 0 ? ` (${scheduledMessages.length})` : ''}
            </span>
          </button>
        </nav>
      </div>

      <div className="space-y-4">
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
          </div>
        ) : activeTab === 'applications' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredApps.map((app) => (
              <div key={app.id} className="glass-card p-5 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-3">
                    <h4 className="text-base font-bold text-emerald-950 line-clamp-1">{app.job_title_snapshot}</h4>
                    <span className="inline-flex px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {app.status}
                    </span>
                  </div>
                  <div className="flex items-center text-xs font-semibold text-emerald-900/70 mb-4">
                    <Building2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                    {app.company_name_snapshot}
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  <button
                    onClick={() => openEmailModal(app)}
                    className="flex-1 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center shadow-md shadow-emerald-500/20"
                  >
                    <Sparkles className="w-4 h-4 mr-1.5" />
                    AI Email
                  </button>
                  <button
                    onClick={() => openDiscoverModal(app)}
                    className="flex-1 py-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-bold transition-all flex items-center justify-center"
                  >
                    <Search className="w-4 h-4 mr-1.5" />
                    Discover
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : activeTab === 'contacts' ? (
          <div className="space-y-3">
            {contacts.length > 0 && (
              <div className="flex justify-end">
                <button
                  onClick={async () => {
                    if (!confirm('Are you sure you want to delete ALL your contacts? This cannot be undone.')) return;
                    try {
                      await fetchApi('/contacts/all', { method: 'DELETE' });
                      setContacts([]);
                    } catch (err: any) {
                      setError(err.message || 'Failed to clear contacts.');
                      setTimeout(() => setError(null), 3000);
                    }
                  }}
                  className="px-3 py-1.5 text-xs font-bold text-rose-600 hover:bg-rose-50 border border-rose-200 rounded-xl transition-colors"
                >
                  Clear All Contacts
                </button>
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredContacts.map((contact) => (
                <div key={contact.id} className="glass-card p-5 flex flex-col">
                  <div className="flex items-center mb-4">
                    <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center text-white font-extrabold text-sm shadow-md shadow-emerald-500/20">
                      {contact.full_name.charAt(0)}
                    </div>
                    <div className="ml-3">
                      <h4 className="text-sm font-bold text-emerald-950">{contact.full_name}</h4>
                      <p className="text-xs text-emerald-900/60 font-medium">{contact.job_title}</p>
                    </div>
                  </div>
                  <div className="space-y-2 mt-auto">
                    {contact.email && (
                      <div className="flex items-center text-xs font-medium text-slate-700 bg-emerald-50/60 px-3 py-2 rounded-xl border border-emerald-100">
                        <Mail className="w-3.5 h-3.5 mr-2 text-emerald-600" />
                        {contact.email}
                      </div>
                    )}
                    {contact.linkedin_url && (
                      <a href={contact.linkedin_url} target="_blank" rel="noreferrer" className="flex items-center text-xs font-semibold text-emerald-700 hover:text-emerald-900 bg-emerald-50 px-3 py-2 rounded-xl border border-emerald-200 transition-colors">
                        <LinkIcon className="w-3.5 h-3.5 mr-2" />
                        LinkedIn Profile
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : activeTab === 'followups' ? (
          <div className="space-y-4">
            {conversationsLoading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
              </div>
            ) : conversations.length === 0 ? (
              <div className="text-center py-16">
                <Mail className="w-12 h-12 text-emerald-300 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-emerald-950">No Conversations Yet</h3>
                <p className="text-sm text-emerald-900/60 mt-1">Send your first outreach email to start a conversation thread.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {conversations.map((conv: any) => (
                  <div key={conv.id} className="glass-card p-5 flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="text-sm font-bold text-emerald-950 line-clamp-1">{conv.subject || 'Untitled Conversation'}</h4>
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          conv.status === 'REPLIED' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                          conv.status === 'SENT' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                          'bg-slate-50 text-slate-600 border-slate-200'
                        }`}>
                          {conv.status}
                        </span>
                      </div>
                      <p className="text-xs text-emerald-800/70 mb-1">
                        <Mail className="w-3 h-3 inline mr-1" />
                        {conv.to_email || 'Unknown recipient'}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {conv.created_at ? new Date(conv.created_at).toLocaleDateString() : ''}
                      </p>
                    </div>
                    <button
                      onClick={() => openFollowUpModal(conv.id, conv.to_email || '')}
                      className="mt-3 w-full py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center shadow-md shadow-emerald-500/20"
                    >
                      <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                      Generate Follow-up
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : activeTab === 'scheduled' ? (
          <div className="space-y-4">
            {scheduledMessagesLoading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-violet-600" />
              </div>
            ) : scheduledMessages.length === 0 ? (
              <div className="text-center py-16">
                <Clock className="w-12 h-12 text-violet-300 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-emerald-950">No Scheduled Emails</h3>
                <p className="text-sm text-emerald-900/60 mt-1">Use “Send Later” in the email composer to schedule emails for future delivery.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {scheduledMessages.map((msg: any) => {
                  const timeInfo = formatScheduledTime(msg.scheduled_at);
                  const isRescheduling = rescheduleId === msg.id;
                  return (
                    <div key={msg.id} className="glass-card p-5 flex flex-col justify-between border-l-4 border-l-violet-400">
                      <div>
                        <div className="flex justify-between items-start mb-2">
                          <h4 className="text-sm font-bold text-emerald-950 line-clamp-1 flex-1 mr-2">{msg.subject || 'Untitled'}</h4>
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-violet-50 text-violet-700 border border-violet-200 flex-shrink-0">
                            <Clock className="w-3 h-3 mr-1" />
                            {timeInfo.relative}
                          </span>
                        </div>
                        <p className="text-xs text-emerald-800/70 mb-1 flex items-center">
                          <Mail className="w-3 h-3 mr-1.5 flex-shrink-0" />
                          {msg.to_email}
                        </p>
                        <p className="text-[11px] text-slate-500 flex items-center">
                          <CalendarClock className="w-3 h-3 mr-1.5 flex-shrink-0" />
                          {timeInfo.absolute}
                        </p>
                        {msg.conversation_subject && (
                          <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">
                            Thread: {msg.conversation_subject}
                          </p>
                        )}
                      </div>

                      {/* Inline reschedule picker */}
                      {isRescheduling && (
                        <div className="mt-3 bg-violet-50 border border-violet-200 rounded-xl p-3 space-y-2 animate-in slide-in-from-top-2 duration-200">
                          <input
                            type="datetime-local"
                            value={rescheduleDateTime}
                            onChange={(e) => setRescheduleDateTime(e.target.value)}
                            min={getMinScheduleDateTime()}
                            className="w-full bg-white border border-violet-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-colors"
                          />
                          <div className="flex space-x-2">
                            <button
                              onClick={() => { setRescheduleId(null); setRescheduleDateTime(''); }}
                              className="flex-1 py-1.5 text-xs font-bold text-slate-600 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg transition-colors"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={async () => {
                                if (!rescheduleDateTime) return;
                                setScheduleActionLoading(msg.id);
                                try {
                                  await fetchApi(`/email/${msg.id}/reschedule`, {
                                    method: 'POST',
                                    body: JSON.stringify({ scheduled_at: new Date(rescheduleDateTime).toISOString() })
                                  });
                                  setRescheduleId(null);
                                  setRescheduleDateTime('');
                                  await loadScheduledMessages();
                                } catch (err: any) {
                                  setError(err.message || 'Failed to reschedule.');
                                  setTimeout(() => setError(null), 3000);
                                } finally {
                                  setScheduleActionLoading(null);
                                }
                              }}
                              disabled={!rescheduleDateTime || scheduleActionLoading === msg.id}
                              className="flex-1 py-1.5 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50 flex justify-center items-center"
                            >
                              {scheduleActionLoading === msg.id ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Confirm'}
                            </button>
                          </div>
                        </div>
                      )}

                      <div className="flex space-x-2 mt-3">
                        <button
                          onClick={() => {
                            setRescheduleId(isRescheduling ? null : msg.id);
                            setRescheduleDateTime('');
                          }}
                          disabled={scheduleActionLoading === msg.id}
                          className="flex-1 py-2 bg-violet-50 hover:bg-violet-100 text-violet-700 border border-violet-200 rounded-xl text-xs font-bold transition-all flex items-center justify-center disabled:opacity-50"
                        >
                          <CalendarClock className="w-3.5 h-3.5 mr-1.5" />
                          Reschedule
                        </button>
                        <button
                          onClick={async () => {
                            if (!confirm('Cancel this scheduled email? It will return to approved status.')) return;
                            setScheduleActionLoading(msg.id);
                            try {
                              await fetchApi(`/email/${msg.id}/cancel-schedule`, { method: 'POST' });
                              setScheduledMessages(prev => prev.filter(m => m.id !== msg.id));
                            } catch (err: any) {
                              setError(err.message || 'Failed to cancel scheduled email.');
                              setTimeout(() => setError(null), 3000);
                            } finally {
                              setScheduleActionLoading(null);
                            }
                          }}
                          disabled={scheduleActionLoading === msg.id}
                          className="flex-1 py-2 bg-rose-50 hover:bg-rose-100 text-rose-600 border border-rose-200 rounded-xl text-xs font-bold transition-all flex items-center justify-center disabled:opacity-50"
                        >
                          {scheduleActionLoading === msg.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5 mr-1.5" />}
                          Cancel
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* AI Generate Email Modal */}
      {isEmailModalOpen && selectedApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="glass-panel w-full max-w-xl p-6 bg-white border border-emerald-100 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center pb-4 border-b border-emerald-100 mb-4">
              <h3 className="text-base font-extrabold text-emerald-950 flex items-center">
                <Sparkles className="w-5 h-5 mr-2 text-emerald-600" />
                AI Outreach Email Assistant
              </h3>
              <button onClick={() => setIsEmailModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              {!aiResult ? (
                <>
                  <p className="text-xs text-emerald-900/80 leading-relaxed">
                    Generate a personalized outreach email for <strong className="text-emerald-950">{selectedApp.job_title_snapshot}</strong> at <strong className="text-emerald-950">{selectedApp.company_name_snapshot}</strong>.
                  </p>
                  
                  <div>
                    <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2">Tone</label>
                    <select
                      value={emailTone}
                      onChange={(e) => setEmailTone(e.target.value)}
                      className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-3 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                    >
                      <option value="professional">Professional</option>
                      <option value="enthusiastic">Enthusiastic</option>
                      <option value="casual">Casual</option>
                      <option value="direct">Direct & Concise</option>
                    </select>
                  </div>

                  <button
                    onClick={handleGenerateEmail}
                    disabled={aiLoading}
                    className="w-full btn-primary py-3 text-xs flex justify-center items-center mt-4"
                  >
                    {aiLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate AI Email ✨'}
                  </button>
                </>
              ) : (
                <div className="space-y-4">
                  {sendSuccess && (
                    <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-3 rounded-xl text-xs font-bold">
                      ✅ {sendSuccess}
                    </div>
                  )}
                  {/* Recipient Email — Contact Selector */}
                  <div>
                    <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1 flex items-center justify-between">
                      <span>Recipient Email</span>
                      {companyContacts.length > 0 && (
                        <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                          {companyContacts.length} contact{companyContacts.length !== 1 ? 's' : ''} found
                        </span>
                      )}
                    </label>
                    {companyContacts.length > 0 ? (
                      <>
                        <select
                          value={recipientEmail}
                          onChange={(e) => setRecipientEmail(e.target.value)}
                          className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors mb-1.5"
                        >
                          {companyContacts.map((c) => (
                            <option key={c.id} value={c.email}>
                              {c.full_name ? `${c.full_name} — ` : ''}{c.job_title ? `${c.job_title} — ` : ''}{c.email}
                            </option>
                          ))}
                          <option value="">✏️ Type custom email...</option>
                        </select>
                        {recipientEmail === '' && (
                          <input
                            type="email"
                            required
                            placeholder="Enter recruiter email manually"
                            value={recipientEmail}
                            onChange={(e) => setRecipientEmail(e.target.value)}
                            className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                          />
                        )}
                      </>
                    ) : (
                      <>
                        <p className="text-[11px] text-amber-700/80 font-medium mb-1.5 leading-tight bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                          ⚠️ No discovered contacts for this company. Enter the recruiter's email manually, or go to the <strong>Contacts</strong> tab to discover contacts first.
                        </p>
                        <input
                          type="email"
                          required
                          placeholder="Enter recruiter email (e.g., john.doe@company.com)"
                          value={recipientEmail}
                          onChange={(e) => setRecipientEmail(e.target.value)}
                          className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                        />
                      </>
                    )}
                  </div>

                  {/* Resume Attachment Picker */}
                  <div>
                    <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1 flex items-center">
                      <Paperclip className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                      Attach Resume
                    </label>
                    <select
                      value={selectedResumeId}
                      onChange={(e) => setSelectedResumeId(e.target.value)}
                      className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                    >
                      <option value="auto">🤖 Auto-detect best resume</option>
                      <option value="none">❌ No attachment</option>
                      {resumes.map((r: any) => (
                        <option key={r.id} value={r.id}>
                          📄 {r.original_filename || 'Master Resume'} (uploaded)
                        </option>
                      ))}
                      {resumeVersions.map((v: any) => (
                        <option key={v.id} value={v.id}>
                          ✨ {v.label || 'Tailored Version'} {v.job_title ? `— ${v.job_title}` : ''}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Subject */}
                  <div>
                    <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1 flex items-center justify-between">
                      <span>Subject</span>
                      {isEdited && (
                        <span className="text-[10px] font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 flex items-center">
                          <Edit3 className="w-3 h-3 mr-1" />
                          Edited
                        </span>
                      )}
                    </label>
                    <input
                      type="text"
                      value={aiResult.subject}
                      onChange={(e) => {
                        setAiResult({ ...aiResult, subject: e.target.value });
                        setIsEdited(true);
                      }}
                      className="w-full bg-white border border-emerald-200/80 rounded-xl px-4 py-2.5 text-xs font-bold text-emerald-950 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                    />
                  </div>

                  {/* Email Body */}
                  <div>
                    <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Email Content</label>
                    <textarea
                      rows={8}
                      value={aiResult.body_text}
                      onChange={(e) => {
                        setAiResult({ ...aiResult, body_text: e.target.value });
                        setIsEdited(true);
                      }}
                      className="w-full bg-white border border-emerald-200/80 rounded-xl px-4 py-3 text-xs font-medium text-slate-900 leading-relaxed resize-y focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => {
                        setAiResult(null);
                        setIsEdited(false);
                      }}
                      className="py-2.5 px-3 text-xs font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-xl transition-colors flex items-center"
                    >
                      <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                      Regenerate
                    </button>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(aiResult.body_text);
                        alert('Email copied to clipboard!');
                      }}
                      className="flex-1 btn-secondary py-2.5 text-xs"
                    >
                      Copy
                    </button>
                    <button
                      onClick={handleSendEmail}
                      disabled={aiLoading}
                      className="flex-1 btn-primary py-2.5 text-xs flex justify-center items-center"
                    >
                      {aiLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                      Send Now
                    </button>
                    <button
                      onClick={() => setShowSchedulePicker(!showSchedulePicker)}
                      disabled={aiLoading}
                      className="flex-1 py-2.5 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-xl text-xs font-bold transition-all flex justify-center items-center shadow-md shadow-violet-500/20 disabled:opacity-50"
                    >
                      <Clock className="w-4 h-4 mr-1.5" />
                      Send Later
                    </button>
                  </div>

                  {/* Schedule Picker */}
                  {showSchedulePicker && (
                    <div className="bg-violet-50 border border-violet-200 rounded-xl p-3 space-y-3 animate-in slide-in-from-top-2 duration-200">
                      <div className="flex items-center space-x-2">
                        <CalendarClock className="w-4 h-4 text-violet-600 flex-shrink-0" />
                        <span className="text-xs font-bold text-violet-900">Schedule for later</span>
                      </div>
                      <input
                        type="datetime-local"
                        value={scheduledDateTime}
                        onChange={(e) => setScheduledDateTime(e.target.value)}
                        min={getMinScheduleDateTime()}
                        className="w-full bg-white border border-violet-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-colors"
                      />
                      <div className="flex space-x-2">
                        <button
                          onClick={() => { setShowSchedulePicker(false); setScheduledDateTime(''); }}
                          className="flex-1 py-2 text-xs font-bold text-violet-700 bg-white hover:bg-violet-100 border border-violet-200 rounded-lg transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleScheduleEmail}
                          disabled={aiLoading || !scheduledDateTime}
                          className="flex-1 py-2 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-lg text-xs font-bold transition-all flex justify-center items-center disabled:opacity-50"
                        >
                          {aiLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CalendarClock className="w-3.5 h-3.5 mr-1" />}
                          Schedule Send
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Discover Contacts Modal */}
      {isDiscoverModalOpen && selectedApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-emerald-950/20 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white/90 backdrop-blur-md border border-emerald-100 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-extrabold text-emerald-950 flex items-center">
                <Search className="w-5 h-5 mr-2 text-emerald-600" />
                Discover Contacts
              </h3>
              <button 
                onClick={() => setIsDiscoverModalOpen(false)}
                className="text-emerald-900/40 hover:text-emerald-900 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Target Company</label>
                <div className="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-xl text-sm font-semibold text-emerald-900">
                  {selectedApp.company_name_snapshot}
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-bold text-emerald-900/70 uppercase tracking-wider mb-2">Company Domain</label>
                <input
                  type="text"
                  placeholder="e.g., stripe.com"
                  value={discoverDomain}
                  onChange={(e) => setDiscoverDomain(e.target.value)}
                  className="block w-full px-3 py-2 border border-emerald-200/80 rounded-xl bg-white/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-sm transition-all"
                />
                <p className="text-[10px] font-medium text-emerald-900/50 mt-2">
                  Enter the company's primary domain to search Hunter.io for recruiters and hiring managers.
                </p>
              </div>
            </div>

            <div className="mt-8">
              <button
                onClick={handleDiscoverContacts}
                disabled={discoverLoading || !discoverDomain.trim()}
                className="w-full btn-primary py-3 rounded-xl shadow-lg shadow-emerald-500/25 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {discoverLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Searching Network...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5 mr-2" />
                    Discover via Hunter.io
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Follow-up Email Modal */}
      {isFollowUpModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="glass-panel w-full max-w-xl p-6 bg-white border border-indigo-100 shadow-2xl animate-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-4 border-b border-indigo-100 mb-4">
              <h3 className="text-base font-extrabold text-indigo-950 flex items-center">
                <Sparkles className="w-5 h-5 mr-2 text-indigo-600" />
                Generate Follow-up Email
              </h3>
              <button onClick={() => setIsFollowUpModalOpen(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            {!followUpResult ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-indigo-900 uppercase tracking-wider mb-2">Follow-up Number</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[1, 2, 3].map((n) => (
                      <button
                        key={n}
                        type="button"
                        onClick={() => setFollowUpNumber(n)}
                        className={`py-2.5 rounded-xl text-xs font-bold transition-all border ${
                          followUpNumber === n
                            ? 'bg-indigo-50 text-indigo-700 border-indigo-300 ring-2 ring-indigo-500/20'
                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                        }`}
                      >
                        {n === 1 ? '1st — Gentle' : n === 2 ? '2nd — Direct' : '3rd — Break-up'}
                      </button>
                    ))}
                  </div>
                  <p className="text-[10px] text-indigo-800/60 mt-2">
                    {followUpNumber === 1 && 'Soft reminder with new value. Best 3-5 days after initial email.'}
                    {followUpNumber === 2 && 'More direct with specific CTA. Best 7-10 days after initial email.'}
                    {followUpNumber === 3 && 'Final "break-up" style — creates urgency. Best 14+ days after initial email.'}
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-indigo-900 uppercase tracking-wider mb-2">Recipient</label>
                  <input
                    type="email"
                    value={followUpRecipient}
                    onChange={(e) => setFollowUpRecipient(e.target.value)}
                    className="w-full bg-slate-50 border border-indigo-200/80 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                  />
                </div>

                <button
                  onClick={handleGenerateFollowUp}
                  disabled={followUpLoading}
                  className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-sm font-bold transition-all flex items-center justify-center shadow-lg shadow-emerald-500/25 disabled:opacity-50"
                >
                  {followUpLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate Follow-up ✨'}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {followUpSendSuccess && (
                  <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-3 rounded-xl text-xs font-bold">
                    ✅ {followUpSendSuccess}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold text-indigo-900 uppercase tracking-wider mb-1 flex items-center justify-between">
                    <span>Subject</span>
                    <span className="flex items-center space-x-2">
                      {followUpEdited && (
                        <span className="text-[10px] font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 flex items-center">
                          <Edit3 className="w-3 h-3 mr-1" />
                          Edited
                        </span>
                      )}
                      <span className="text-[10px] font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200">
                        Follow-up #{followUpNumber}
                      </span>
                    </span>
                  </label>
                  <input
                    type="text"
                    value={followUpResult.subject}
                    onChange={(e) => {
                      setFollowUpResult({ ...followUpResult, subject: e.target.value });
                      setFollowUpEdited(true);
                    }}
                    className="w-full bg-white border border-indigo-200/80 rounded-xl px-4 py-2.5 text-xs font-bold text-indigo-950 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-indigo-900 uppercase tracking-wider mb-1">Email Content</label>
                  <textarea
                    rows={10}
                    value={followUpResult.body_text}
                    onChange={(e) => {
                      setFollowUpResult({ ...followUpResult, body_text: e.target.value });
                      setFollowUpEdited(true);
                    }}
                    className="w-full bg-white border border-indigo-200/80 rounded-xl px-4 py-3 text-xs font-medium text-slate-900 leading-relaxed resize-y focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                  />
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => {
                      setFollowUpResult(null);
                      setFollowUpEdited(false);
                    }}
                    className="py-2.5 px-3 text-xs font-bold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-xl transition-colors flex items-center"
                  >
                    <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                    Regenerate
                  </button>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(followUpResult.body_text);
                      alert('Follow-up copied!');
                    }}
                    className="flex-1 btn-secondary py-2.5 text-xs"
                  >
                    Copy
                  </button>
                  <button
                    onClick={handleSendFollowUp}
                    disabled={followUpLoading}
                    className="flex-1 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-xs font-bold transition-all flex justify-center items-center shadow-md shadow-emerald-500/20 disabled:opacity-50"
                  >
                    {followUpLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                    Send Now
                  </button>
                  <button
                    onClick={() => setShowFollowUpSchedulePicker(!showFollowUpSchedulePicker)}
                    disabled={followUpLoading}
                    className="flex-1 py-2.5 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-xl text-xs font-bold transition-all flex justify-center items-center shadow-md shadow-violet-500/20 disabled:opacity-50"
                  >
                    <Clock className="w-4 h-4 mr-1.5" />
                    Send Later
                  </button>
                </div>

                {/* Follow-up Schedule Picker */}
                {showFollowUpSchedulePicker && (
                  <div className="bg-violet-50 border border-violet-200 rounded-xl p-3 space-y-3 animate-in slide-in-from-top-2 duration-200">
                    <div className="flex items-center space-x-2">
                      <CalendarClock className="w-4 h-4 text-violet-600 flex-shrink-0" />
                      <span className="text-xs font-bold text-violet-900">Schedule follow-up for later</span>
                    </div>
                    <input
                      type="datetime-local"
                      value={followUpScheduledDateTime}
                      onChange={(e) => setFollowUpScheduledDateTime(e.target.value)}
                      min={getMinScheduleDateTime()}
                      className="w-full bg-white border border-violet-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-colors"
                    />
                    <div className="flex space-x-2">
                      <button
                        onClick={() => { setShowFollowUpSchedulePicker(false); setFollowUpScheduledDateTime(''); }}
                        className="flex-1 py-2 text-xs font-bold text-violet-700 bg-white hover:bg-violet-100 border border-violet-200 rounded-lg transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleScheduleFollowUp}
                        disabled={followUpLoading || !followUpScheduledDateTime}
                        className="flex-1 py-2 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white rounded-lg text-xs font-bold transition-all flex justify-center items-center disabled:opacity-50"
                      >
                        {followUpLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CalendarClock className="w-3.5 h-3.5 mr-1" />}
                        Schedule Send
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
