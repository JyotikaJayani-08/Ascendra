'use client';

import { useState, useEffect } from 'react';
import { UploadCloud, FileText, Loader2, CheckCircle2, Clock, Search, Sparkles, Trash2, AlertTriangle, Eye, X, Send, CheckSquare, Square, Download, Printer, RefreshCw } from 'lucide-react';
import { fetchApi, fetchApiFormData } from '@/lib/api';
import Link from 'next/link';
import LinkifiedText from '@/components/common/LinkifiedText';

interface Resume {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  status: string;
  structured_data?: any;
  raw_text?: string;
  created_at: string;
}

interface ResumeVersion {
  id: string;
  resume_id: string;
  version_number: number;
  label: string;
  markdown_content?: string;
  structured_data?: any;
  created_at: string;
  source: string;
  status: string;
}

function extractAtsScore(data: any): number | null {
  if (data == null) return null;
  let parsed = data;
  if (typeof data === 'string') {
    try {
      parsed = JSON.parse(data);
    } catch {
      return null;
    }
  }
  if (typeof parsed === 'number') return parsed;
  if (parsed?.ats_score != null) return Number(parsed.ats_score);
  if (parsed?.structured_data?.ats_score != null) return Number(parsed.structured_data.ats_score);
  return null;
}

function extractMatchedKeywords(data: any): string[] {
  if (data == null) return [];
  let parsed = data;
  if (typeof data === 'string') {
    try {
      parsed = JSON.parse(data);
    } catch {
      return [];
    }
  }
  const kws = parsed?.matched_keywords ?? parsed?.structured_data?.matched_keywords;
  return Array.isArray(kws) ? kws : [];
}

function getResumePreviewText(content: string | undefined): string {
  if (!content) return 'Optimized resume content tailored for role requirements.';
  if (content.trim().startsWith('{')) {
    try {
      const parsed = JSON.parse(content);
      const summary = parsed?.structured_data?.summary || parsed?.summary;
      if (summary) return summary;
    } catch {
      // fallback
    }
  }
  return content.substring(0, 150) + '...';
}

export default function ResumesPage() {
  const [activeTab, setActiveTab] = useState<'uploaded' | 'tailored'>('uploaded');
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [tailoredVersions, setTailoredVersions] = useState<ResumeVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Selection State
  const [selectedUploadedIds, setSelectedUploadedIds] = useState<string[]>([]);
  const [selectedTailoredIds, setSelectedTailoredIds] = useState<string[]>([]);

  // Modals
  const [deletingResume, setDeletingResume] = useState<Resume | null>(null);
  const [deletingVersion, setDeletingVersion] = useState<ResumeVersion | null>(null);
  const [isConfirmDeleteAllOpen, setIsConfirmDeleteAllOpen] = useState(false);
  const [isConfirmBulkDeleteOpen, setIsConfirmBulkDeleteOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [viewVersion, setViewVersion] = useState<ResumeVersion | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareData, setCompareData] = useState<any>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  const handlePrintPdf = (markdown: string, title: string) => {
    if (!markdown) return;

    const parseInline = (text: string) => {
      return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code style="background:#f1f5f9;padding:1px 4px;border-radius:3px;font-size:10px;">$1</code>');
    };

    const lines = markdown.split('\n');
    let htmlContent = '';
    let inList = false;

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        continue;
      }

      if (trimmed.startsWith('# ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h1 style="font-size: 22px; font-weight: 800; color: #0f172a; margin-top: 0; margin-bottom: 6px; border-bottom: 2px solid #059669; padding-bottom: 4px;">${parseInline(trimmed.substring(2))}</h1>`;
      } else if (trimmed.startsWith('## ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h2 style="font-size: 14px; font-weight: 700; color: #047857; margin-top: 16px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e2e8f0; padding-bottom: 2px;">${parseInline(trimmed.substring(3))}</h2>`;
      } else if (trimmed.startsWith('### ')) {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<h3 style="font-size: 13px; font-weight: 700; color: #1e293b; margin-top: 10px; margin-bottom: 4px;">${parseInline(trimmed.substring(4))}</h3>`;
      } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (!inList) { htmlContent += '<ul style="margin: 4px 0 8px 18px; padding: 0; list-style-type: disc;">'; inList = true; }
        htmlContent += `<li style="font-size: 11px; color: #334155; margin-bottom: 3px; line-height: 1.4;">${parseInline(trimmed.substring(2))}</li>`;
      } else {
        if (inList) { htmlContent += '</ul>'; inList = false; }
        htmlContent += `<p style="font-size: 11px; color: #334155; margin: 4px 0 8px 0; line-height: 1.5;">${parseInline(trimmed)}</p>`;
      }
    }
    if (inList) htmlContent += '</ul>';

    const printWindow = window.open('', '_blank', 'width=850,height=1100');
    if (!printWindow) {
      alert('Please allow popups to export or print your PDF.');
      return;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>${title || 'Tailored_Resume'}</title>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
            @page { size: A4; margin: 12mm 15mm; }
            body { font-family: 'Inter', system-ui, -apple-system, sans-serif; margin: 0; padding: 24px; background: white; color: #1e293b; }
            @media print {
              body { padding: 0; }
              .no-print { display: none !important; }
            }
          </style>
        </head>
        <body>
          <div class="no-print" style="background:#ecfdf5;padding:12px 20px;border-bottom:1px solid #a7f3d0;margin:-24px -24px 20px -24px;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:12px;font-weight:700;color:#047857;">📄 Print / PDF Export Preview</span>
            <button onclick="window.print()" style="background:#059669;color:white;border:none;padding:8px 18px;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;box-shadow:0 2px 4px rgba(0,0,0,0.1);">
              🖨️ Save as PDF / Print
            </button>
          </div>
          ${htmlContent}
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [resData, verData] = await Promise.all([
        fetchApi('/resumes').catch(() => []),
        fetchApi('/resume-versions').catch(() => []),
      ]);
      const resItems = resData.items || resData || [];
      const verItems = Array.isArray(verData) ? verData : (verData.items || []);
      setResumes(resItems);
      setTailoredVersions(verItems);
      setSelectedUploadedIds([]);
      setSelectedTailoredIds([]);
    } catch (err: any) {
      console.error('Failed to load resume vault data:', err);
      setError('Could not load resume vault. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      await fetchApiFormData('/resumes', formData);
      setSuccess('Resume uploaded & parsed successfully!');
      setTimeout(() => setSuccess(null), 3000);
      await loadAllData();
    } catch (err: any) {
      setError(err.message || 'Failed to upload resume. Please try again.');
      setTimeout(() => setError(null), 5000);
    } finally {
      setUploading(false);
    }
  };

  // Single Deletions
  const handleDeleteResume = async () => {
    if (!deletingResume) return;
    setDeleteLoading(true);
    try {
      await fetchApi(`/resumes/${deletingResume.id}`, { method: 'DELETE' });
      setSuccess('Resume permanently deleted!');
      setTimeout(() => setSuccess(null), 3000);
      setDeletingResume(null);
      await loadAllData();
    } catch (err: any) {
      setError(err.message || 'Failed to delete resume');
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleDeleteVersion = async () => {
    if (!deletingVersion) return;
    setDeleteLoading(true);
    try {
      await fetchApi(`/resume-versions/${deletingVersion.id}`, { method: 'DELETE' });
      setSuccess('Tailored version deleted!');
      setTimeout(() => setSuccess(null), 3000);
      setDeletingVersion(null);
      await loadAllData();
    } catch (err: any) {
      setError(err.message || 'Failed to delete version');
    } finally {
      setDeleteLoading(false);
    }
  };

  // Bulk Deletions
  const handleBulkDelete = async () => {
    setDeleteLoading(true);
    try {
      if (activeTab === 'uploaded') {
        const res = await fetchApi('/resumes/bulk-delete', {
          method: 'POST',
          body: JSON.stringify({ ids: selectedUploadedIds }),
        });
        setSuccess(`Successfully deleted ${res.deleted_count || selectedUploadedIds.length} resumes!`);
      } else {
        const res = await fetchApi('/resume-versions/bulk-delete', {
          method: 'POST',
          body: JSON.stringify({ ids: selectedTailoredIds }),
        });
        setSuccess(`Successfully deleted ${res.deleted_count || selectedTailoredIds.length} tailored versions!`);
      }
      setTimeout(() => setSuccess(null), 3000);
      setIsConfirmBulkDeleteOpen(false);
      await loadAllData();
    } catch (err: any) {
      setError(err.message || 'Bulk delete failed');
    } finally {
      setDeleteLoading(false);
    }
  };

  // Delete All
  const handleDeleteAll = async () => {
    setDeleteLoading(true);
    try {
      if (activeTab === 'uploaded') {
        const res = await fetchApi('/resumes/delete-all', { method: 'DELETE' });
        setSuccess(`Cleared all ${res.deleted_count || 0} uploaded resumes!`);
      } else {
        const res = await fetchApi('/resume-versions/delete-all', { method: 'DELETE' });
        setSuccess(`Cleared all ${res.deleted_count || 0} tailored resume versions!`);
      }
      setTimeout(() => setSuccess(null), 3000);
      setIsConfirmDeleteAllOpen(false);
      await loadAllData();
    } catch (err: any) {
      setError(err.message || 'Delete all failed');
    } finally {
      setDeleteLoading(false);
    }
  };

  // Checkbox helpers
  const toggleSelectUploaded = (id: string) => {
    setSelectedUploadedIds(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const toggleSelectTailored = (id: string) => {
    setSelectedTailoredIds(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const filteredResumes = resumes.filter(r =>
    r.original_filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredVersions = tailoredVersions.filter(v =>
    (v.label || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (v.markdown_content || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const isAllUploadedSelected = filteredResumes.length > 0 && selectedUploadedIds.length === filteredResumes.length;
  const isAllTailoredSelected = filteredVersions.length > 0 && selectedTailoredIds.length === filteredVersions.length;

  const toggleSelectAllUploaded = () => {
    if (isAllUploadedSelected) {
      setSelectedUploadedIds([]);
    } else {
      setSelectedUploadedIds(filteredResumes.map(r => r.id));
    }
  };

  const toggleSelectAllTailored = () => {
    if (isAllTailoredSelected) {
      setSelectedTailoredIds([]);
    } else {
      setSelectedTailoredIds(filteredVersions.map(v => v.id));
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      {/* Informative Header Banner */}
      <div className="bg-gradient-to-r from-emerald-900/90 to-teal-900/90 text-white p-4 rounded-2xl shadow-md border border-emerald-700/50">
        <div className="flex items-start space-x-3">
          <div className="p-2 bg-emerald-500/20 rounded-xl mt-0.5">
            <Sparkles className="w-5 h-5 text-emerald-300" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-emerald-100">Resume Vault & AI Version Management</h3>
            <p className="text-xs text-emerald-200/80 mt-0.5 leading-relaxed">
              Upload your base resume below. When you click <strong>"Tailor Resume with AI"</strong> on jobs, optimized versions are stored in the <strong>AI Tailored Resumes</strong> tab below!
            </p>
          </div>
        </div>
      </div>

      {/* Title & Tabs Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-emerald-950 mb-1">Resume Vault</h2>
          <p className="text-emerald-900/70 font-medium">Switch between uploaded master resumes and AI-tailored job versions.</p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          {/* Tab Controls */}
          <div className="flex bg-emerald-100/70 p-1 rounded-xl border border-emerald-200/60 backdrop-blur-sm">
            <button
              onClick={() => setActiveTab('uploaded')}
              className={`flex items-center px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === 'uploaded' ? 'bg-white text-emerald-900 shadow-sm' : 'text-emerald-800/70 hover:text-emerald-950'
                }`}
            >
              <FileText className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
              Uploaded ({resumes.length})
            </button>
            <button
              onClick={() => setActiveTab('tailored')}
              className={`flex items-center px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === 'tailored' ? 'bg-white text-emerald-900 shadow-sm' : 'text-emerald-800/70 hover:text-emerald-950'
                }`}
            >
              <Sparkles className="w-3.5 h-3.5 mr-1.5 text-amber-500" />
              AI Tailored ({tailoredVersions.length})
            </button>
          </div>

          <div className="relative w-full sm:w-56">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-emerald-600/50" />
            </div>
            <input
              type="text"
              placeholder="Search vault..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-emerald-200/80 rounded-xl bg-white/90 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 text-sm transition-all shadow-sm"
            />
          </div>
        </div>
      </div>

      {/* Bulk Action & Delete-All Toolbar */}
      <div className="glass-panel p-3 flex flex-wrap items-center justify-between gap-3 border border-emerald-100">
        <div className="flex items-center space-x-3">
          {activeTab === 'uploaded' ? (
            <button
              onClick={toggleSelectAllUploaded}
              disabled={filteredResumes.length === 0}
              className="flex items-center text-xs font-bold text-emerald-900 hover:text-emerald-600 transition-colors"
            >
              {isAllUploadedSelected ? (
                <CheckSquare className="w-4 h-4 mr-1.5 text-emerald-600" />
              ) : (
                <Square className="w-4 h-4 mr-1.5 text-slate-400" />
              )}
              Select All Uploaded ({filteredResumes.length})
            </button>
          ) : (
            <button
              onClick={toggleSelectAllTailored}
              disabled={filteredVersions.length === 0}
              className="flex items-center text-xs font-bold text-emerald-900 hover:text-emerald-600 transition-colors"
            >
              {isAllTailoredSelected ? (
                <CheckSquare className="w-4 h-4 mr-1.5 text-emerald-600" />
              ) : (
                <Square className="w-4 h-4 mr-1.5 text-slate-400" />
              )}
              Select All AI Tailored ({filteredVersions.length})
            </button>
          )}

          {((activeTab === 'uploaded' && selectedUploadedIds.length > 0) ||
            (activeTab === 'tailored' && selectedTailoredIds.length > 0)) && (
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg">
                {activeTab === 'uploaded' ? selectedUploadedIds.length : selectedTailoredIds.length} Selected
              </span>
            )}
        </div>

        <div className="flex items-center space-x-2">
          {((activeTab === 'uploaded' && selectedUploadedIds.length > 0) ||
            (activeTab === 'tailored' && selectedTailoredIds.length > 0)) && (
              <button
                onClick={() => setIsConfirmBulkDeleteOpen(true)}
                className="px-3.5 py-1.5 bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 rounded-xl text-xs font-bold transition-all flex items-center shadow-sm"
              >
                <Trash2 className="w-3.5 h-3.5 mr-1.5 text-rose-500" />
                Delete Selected ({activeTab === 'uploaded' ? selectedUploadedIds.length : selectedTailoredIds.length})
              </button>
            )}

          {((activeTab === 'uploaded' && resumes.length > 0) ||
            (activeTab === 'tailored' && tailoredVersions.length > 0)) && (
              <button
                onClick={() => setIsConfirmDeleteAllOpen(true)}
                className="px-3.5 py-1.5 bg-slate-100 text-slate-700 hover:bg-rose-600 hover:text-white rounded-xl text-xs font-bold transition-all flex items-center"
              >
                <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                Delete All {activeTab === 'uploaded' ? 'Uploaded' : 'Tailored'}
              </button>
            )}
        </div>
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

      {/* Tab Content: Uploaded Base Resumes */}
      {activeTab === 'uploaded' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Upload Zone */}
          <div className="lg:col-span-1">
            <div className="relative overflow-hidden glass-panel p-8 flex flex-col items-center justify-center text-center group transition-all hover:border-emerald-400">
              <input
                type="file"
                accept=".pdf"
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                onChange={handleFileUpload}
                disabled={uploading}
              />
              <div className="p-4 rounded-2xl bg-emerald-50 text-emerald-600 mb-4 group-hover:bg-emerald-600 group-hover:text-white group-hover:scale-110 transition-all shadow-sm">
                {uploading ? (
                  <Loader2 className="h-8 w-8 animate-spin" />
                ) : (
                  <UploadCloud className="h-8 w-8" />
                )}
              </div>
              <h3 className="text-base font-extrabold text-emerald-950 mb-1">Upload Base Resume</h3>
              <p className="text-xs text-emerald-900/60 font-medium">Drag PDF file or click to browse (Max 5MB)</p>
            </div>
          </div>

          {/* List */}
          <div className="lg:col-span-2 space-y-3">
            {loading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
              </div>
            ) : filteredResumes.length === 0 ? (
              <div className="glass-panel p-12 text-center">
                <FileText className="h-12 w-12 text-emerald-500 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-emerald-950 mb-1">No uploaded base resumes found</h3>
                <p className="text-sm text-emerald-800/70">Upload your master PDF resume to get started.</p>
              </div>
            ) : (
              filteredResumes.map((resume) => {
                const isSelected = selectedUploadedIds.includes(resume.id);
                return (
                  <div
                    key={resume.id}
                    className={`glass-card p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border transition-all ${isSelected ? 'border-emerald-500 bg-emerald-50/30' : 'border-emerald-100/80'
                      }`}
                  >
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => toggleSelectUploaded(resume.id)}
                        className="text-emerald-700 hover:text-emerald-900 p-1"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-emerald-600" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-400" />
                        )}
                      </button>
                      <div className="p-3 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
                        <FileText className="h-5 w-5" />
                      </div>
                      <div>
                        <p className="text-sm font-bold text-emerald-950">{resume.original_filename}</p>
                        <p className="text-xs text-emerald-900/60 font-medium">
                          {(resume.file_size_bytes / 1024).toFixed(1)} KB • Added {new Date(resume.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
                      {resume.status === 'READY' || resume.status === 'PARSED' ? (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-500" />
                          Parsed
                        </span>
                      ) : (
                        <button
                          onClick={async () => {
                            try {
                              await fetchApi(`/resumes/${resume.id}/reparse`, { method: 'POST' });
                              setSuccess('Parsing re-triggered!');
                              setTimeout(() => setSuccess(null), 3000);
                              await loadAllData();
                            } catch (err: any) {
                              setError('Failed to reparse resume');
                            }
                          }}
                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition-colors"
                          title="Click to re-trigger parsing"
                        >
                          <Clock className="w-3.5 h-3.5 mr-1 animate-pulse text-amber-500" />
                          Re-parse
                        </button>
                      )}

                      <button
                        onClick={() => setDeletingResume(resume)}
                        className="p-2 text-rose-500 hover:bg-rose-50 rounded-xl transition-colors text-xs font-bold flex items-center"
                        title="Delete Resume"
                      >
                        <Trash2 className="w-3.5 h-3.5 mr-1" />
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Tab Content: AI Tailored Resumes */}
      {activeTab === 'tailored' && (
        <div className="space-y-4">
          {loading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
            </div>
          ) : filteredVersions.length === 0 ? (
            <div className="glass-panel p-12 text-center">
              <Sparkles className="h-12 w-12 text-amber-500 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-emerald-950 mb-1">No AI Tailored Resumes Yet</h3>
              <p className="text-sm text-emerald-800/70 mb-4">Go to Target Jobs and click "Tailor Resume with AI" on any position!</p>
              <Link href="/dashboard/jobs" className="btn-primary inline-flex items-center text-xs">
                Browse Target Jobs &rarr;
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredVersions.map((ver) => {
                const isSelected = selectedTailoredIds.includes(ver.id);
                return (
                  <div
                    key={ver.id}
                    className={`glass-card p-5 border transition-all flex flex-col justify-between ${isSelected ? 'border-emerald-500 bg-emerald-50/20 shadow-md' : 'border-emerald-100 hover:border-emerald-300'
                      }`}
                  >
                    <div>
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => toggleSelectTailored(ver.id)}
                            className="text-emerald-700 hover:text-emerald-900"
                          >
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-emerald-600" />
                            ) : (
                              <Square className="w-4 h-4 text-slate-400" />
                            )}
                          </button>
                          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200 flex items-center">
                            <Sparkles className="w-3 h-3 mr-1" />
                            v{ver.version_number} • AI Tailored
                          </span>
                        </div>
                        <span className="text-[11px] text-emerald-800/60 font-medium">
                          {new Date(ver.created_at).toLocaleDateString()}
                        </span>
                      </div>

                      <h4 className="font-extrabold text-emerald-950 text-base mb-1">
                        {ver.label || `Tailored Version v${ver.version_number}`}
                      </h4>

                      {/* ATS Score & Keyword Match Badge */}
                      <div className="flex flex-wrap items-center gap-2 my-2.5">
                        {(() => {
                          const score = extractAtsScore(ver.structured_data);
                          if (score != null) {
                            return (
                              <>
                                <span className="px-2.5 py-1 rounded-lg text-xs font-black bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center shadow-xs">
                                  🎯 ATS Match: <span className="ml-1 text-emerald-600 font-extrabold font-mono">{score}%</span>
                                </span>
                                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-md border ${
                                  score >= 90
                                    ? 'text-emerald-800 bg-emerald-50/80 border-emerald-200'
                                    : score >= 75
                                    ? 'text-teal-800 bg-teal-50/80 border-teal-200'
                                    : score >= 60
                                    ? 'text-amber-800 bg-amber-50/80 border-amber-200'
                                    : score >= 40
                                    ? 'text-orange-800 bg-orange-50/80 border-orange-200'
                                    : 'text-rose-800 bg-rose-50/80 border-rose-200'
                                }`}>
                                  {score >= 90 ? '🔥 Excellent Match'
                                    : score >= 75 ? '✅ Strong Match'
                                    : score >= 60 ? '📊 Moderate Match'
                                    : score >= 40 ? '⚠️ Needs Improvement'
                                    : '🔻 Low Match'}
                                </span>
                              </>
                            );
                          }
                          return (
                            <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-50 text-slate-500 border border-slate-200 flex items-center">
                              🎯 ATS Score: <span className="ml-1 font-mono">Pending</span>
                            </span>
                          );
                        })()}
                      </div>

                      {/* Keyword Pills */}
                      {(() => {
                        const keywords = extractMatchedKeywords(ver.structured_data);
                        if (keywords.length === 0) return null;
                        return (
                          <div className="flex flex-wrap gap-1 mb-3">
                            {keywords.slice(0, 4).map((kw: string, idx: number) => (
                              <span key={idx} className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                                ✓ {kw}
                              </span>
                            ))}
                            {keywords.length > 4 && (
                              <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-slate-50 text-slate-500">
                                +{keywords.length - 4} more
                              </span>
                            )}
                          </div>
                        );
                      })()}

                      <p className="text-xs text-emerald-900/70 font-medium line-clamp-3 mb-4">
                        <LinkifiedText text={getResumePreviewText(ver.markdown_content)} />
                      </p>
                    </div>

                    <div className="flex items-center space-x-2 pt-3 border-t border-emerald-100/60">
                      <button
                        onClick={() => setViewVersion(ver)}
                        className="flex-1 py-2 px-3 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-bold transition-colors flex items-center justify-center"
                      >
                        <Eye className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                        View
                      </button>
                      <button
                        onClick={() => handlePrintPdf(ver.markdown_content || '', ver.label || 'Tailored_Resume')}
                        className="py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded-xl text-xs font-bold transition-colors flex items-center justify-center"
                        title="Export / Print PDF"
                      >
                        <Printer className="w-3.5 h-3.5 text-slate-600" />
                      </button>
                      <Link
                        href="/dashboard/outreach"
                        className="py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-colors flex items-center justify-center shadow-sm"
                      >
                        <Send className="w-3.5 h-3.5 mr-1" />
                        Outreach
                      </Link>
                      <button
                        onClick={() => setDeletingVersion(ver)}
                        className="p-2 text-rose-500 hover:bg-rose-50 rounded-xl transition-colors text-xs font-bold"
                        title="Delete Version"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* View Tailored Resume Modal with ATS Screening Report & Side-by-Side Compare */}
      {viewVersion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className={`glass-panel w-full ${compareMode ? 'max-w-5xl' : 'max-w-3xl'} p-6 bg-white border border-emerald-100 shadow-2xl animate-in zoom-in-95 duration-200 max-h-[88vh] flex flex-col transition-all duration-300`}>
            <div className="flex justify-between items-center pb-4 border-b border-emerald-100 mb-4 flex-shrink-0">
              <div>
                <h3 className="text-base font-extrabold text-emerald-950 flex items-center">
                  <Sparkles className="w-5 h-5 mr-2 text-amber-500" />
                  {viewVersion.label || `Tailored Version v${viewVersion.version_number}`}
                </h3>
                <p className="text-xs text-emerald-800/70 mt-0.5">Created on {new Date(viewVersion.created_at).toLocaleString()}</p>
              </div>

              <div className="flex items-center space-x-3">
                {/* Side-by-Side Compare Toggle */}
                <button
                  onClick={async () => {
                    if (!compareMode && viewVersion) {
                      setCompareLoading(true);
                      try {
                        const res = await fetchApi(`/resume-versions/${viewVersion.id}/compare`);
                        setCompareData(res);
                      } catch (err) {
                        console.error('Failed to fetch backend comparison:', err);
                      } finally {
                        setCompareLoading(false);
                      }
                    }
                    setCompareMode(!compareMode);
                  }}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center border ${
                    compareMode
                      ? 'bg-emerald-600 text-white border-emerald-600 shadow-md shadow-emerald-500/20'
                      : 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
                  }`}
                >
                  {compareLoading ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5 mr-1.5" />}
                  {compareMode ? '⚡ Compare Mode (Active)' : '⚡ Side-by-Side Compare'}
                </button>

                <button onClick={() => { setViewVersion(null); setCompareMode(false); setCompareData(null); }} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* ATS Match Report Panel */}
            <div className="mb-4 bg-emerald-50/80 border border-emerald-200/80 rounded-xl p-3.5 flex flex-col space-y-2 flex-shrink-0">
              {(() => {
                const score = extractAtsScore(viewVersion.structured_data);
                return (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-black text-emerald-950 uppercase tracking-wider">🎯 ATS Match Score:</span>
                      {score != null ? (
                        <span className="text-sm font-extrabold text-emerald-700 bg-white px-2 py-0.5 rounded-md border border-emerald-300 shadow-xs font-mono">
                          {score}%
                        </span>
                      ) : (
                        <span className="text-sm font-bold text-slate-500 bg-white px-2 py-0.5 rounded-md border border-slate-200 font-mono">
                          Pending
                        </span>
                      )}
                    </div>
                    {score != null && (
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-md border ${
                        score >= 90
                          ? 'text-emerald-800 bg-emerald-100 border-emerald-200'
                          : score >= 75
                          ? 'text-teal-800 bg-teal-100 border-teal-200'
                          : score >= 60
                          ? 'text-amber-800 bg-amber-100 border-amber-200'
                          : score >= 40
                          ? 'text-orange-800 bg-orange-100 border-orange-200'
                          : 'text-rose-800 bg-rose-100 border-rose-200'
                      }`}>
                        {score >= 90 ? '🔥 Excellent Match'
                          : score >= 75 ? '✅ Strong Match'
                          : score >= 60 ? '📊 Moderate Match'
                          : score >= 40 ? '⚠️ Needs Improvement'
                          : '🔻 Low Match'}
                      </span>
                    )}
                  </div>
                );
              })()}

              {(viewVersion.structured_data as any)?.ats_feedback && (
                <p className="text-xs text-emerald-900/80 font-medium leading-tight">
                  💡 {(viewVersion.structured_data as any).ats_feedback}
                </p>
              )}

              {Array.isArray((viewVersion.structured_data as any)?.matched_keywords) && (viewVersion.structured_data as any).matched_keywords.length > 0 && (
                <div className="flex flex-wrap items-center gap-1 pt-1">
                  <span className="text-[11px] font-bold text-emerald-900 mr-1">Matched Keywords:</span>
                  {(viewVersion.structured_data as any).matched_keywords.map((kw: string, idx: number) => (
                    <span key={idx} className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-white text-emerald-800 border border-emerald-200">
                      ✓ {kw}
                    </span>
                  ))}
                </div>
              )}

              {Array.isArray(compareData?.added_keywords) && compareData.added_keywords.length > 0 && (
                <div className="flex flex-wrap items-center gap-1 pt-0.5">
                  <span className="text-[11px] font-bold text-amber-900 mr-1">✨ Newly Added Keywords by AI:</span>
                  {compareData.added_keywords.map((kw: string, idx: number) => (
                    <span key={idx} className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-300">
                      + {kw}
                    </span>
                  ))}
                </div>
              )}

              {Array.isArray((viewVersion.structured_data as any)?.missing_skills) && (viewVersion.structured_data as any).missing_skills.length > 0 && (
                <div className="flex flex-wrap items-center gap-1 pt-0.5">
                  <span className="text-[11px] font-bold text-rose-900 mr-1">Missing Role Skills:</span>
                  {(viewVersion.structured_data as any).missing_skills.map((kw: string, idx: number) => (
                    <span key={idx} className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                      ✗ {kw}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Content View: Single vs Side-by-Side Comparison */}
            {compareMode ? (
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 overflow-hidden">
                {/* Left: Original Base Resume */}
                {(() => {
                  const orig = resumes.find(r => r.id === viewVersion.resume_id);
                  const rawSkills = compareData?.original_skills || (Array.isArray(orig?.structured_data?.skills) ? orig.structured_data.skills : []);
                  const baseScore = compareData?.original_ats_score ?? 40;
                  return (
                    <div className="flex flex-col h-full overflow-hidden bg-slate-50 border border-slate-200 rounded-xl p-4">
                      <div className="flex justify-between items-center pb-2 mb-2 border-b border-slate-200 flex-shrink-0">
                        <span className="text-xs font-extrabold text-slate-800 flex items-center">
                          <FileText className="w-4 h-4 mr-1.5 text-slate-600" />
                          Original Base Resume
                        </span>
                        <span className="text-[10px] font-bold text-slate-700 bg-slate-200 px-2 py-0.5 rounded border border-slate-300">
                          Base ATS: ~{baseScore}%
                        </span>
                      </div>
                      
                      <div className="text-[11px] text-slate-600 mb-2 font-bold">
                        📄 File: <span className="font-mono text-slate-800">{orig?.original_filename || 'Master PDF'}</span>
                      </div>

                      {rawSkills.length > 0 && (
                        <div className="mb-2.5 flex flex-wrap gap-1 flex-shrink-0">
                          <span className="text-[10px] font-bold text-slate-600 w-full mb-0.5">Original Extracted Skills ({rawSkills.length}):</span>
                          {rawSkills.slice(0, 10).map((sk: string, i: number) => (
                            <span key={i} className="text-[9px] font-semibold bg-white text-slate-700 border border-slate-200 px-1.5 py-0.5 rounded">
                              {sk}
                            </span>
                          ))}
                          {rawSkills.length > 10 && (
                            <span className="text-[9px] font-semibold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                              +{rawSkills.length - 10} more
                            </span>
                          )}
                        </div>
                      )}
                      
                      <div className="flex-1 overflow-y-auto text-[11px] text-slate-700 font-mono whitespace-pre-wrap leading-relaxed shadow-inner bg-white p-3 rounded-lg border border-slate-200">
                        <LinkifiedText text={compareData?.original_text_snippet || orig?.raw_text || orig?.structured_data?.summary || 'Original resume parsed successfully.'} />
                      </div>
                    </div>
                  );
                })()}

                {/* Right: AI Tailored Version */}
                <div className="flex flex-col h-full overflow-hidden bg-emerald-50/50 border border-emerald-200 rounded-xl p-4">
                  <div className="flex justify-between items-center pb-2 mb-2 border-b border-emerald-200 flex-shrink-0">
                    <span className="text-xs font-extrabold text-emerald-950 flex items-center">
                      <Sparkles className="w-4 h-4 mr-1.5 text-amber-500" />
                      AI Tailored Version
                    </span>
                    
                    {/* Sibling Version Selector Dropdown */}
                    {Array.isArray(compareData?.sibling_versions) && compareData.sibling_versions.length > 1 && (
                      <select
                        value={viewVersion.id}
                        onChange={async (e) => {
                          const targetId = e.target.value;
                          const selectedVer = tailoredVersions.find(v => v.id === targetId);
                          if (selectedVer) {
                            setViewVersion(selectedVer);
                            setCompareLoading(true);
                            try {
                              const res = await fetchApi(`/resume-versions/${selectedVer.id}/compare`);
                              setCompareData(res);
                            } catch (err) {
                              console.error('Failed to load version compare:', err);
                            } finally {
                              setCompareLoading(false);
                            }
                          }
                        }}
                        className="bg-white border border-emerald-300 rounded-lg px-2 py-0.5 text-[10px] font-bold text-emerald-900 focus:ring-1 focus:ring-emerald-500"
                      >
                        {compareData.sibling_versions.map((sib: any) => (
                          <option key={sib.id} value={sib.id}>
                            v{sib.version_number} — {sib.label}
                          </option>
                        ))}
                      </select>
                    )}

                    <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-300">
                      ATS Match: {extractAtsScore(viewVersion.structured_data) ?? compareData?.ats_score ?? 'N/A'}%
                      {compareData?.score_improvement > 0 && (
                        <span className="ml-1 text-emerald-700 font-black">(+{compareData.score_improvement}%)</span>
                      )}
                    </span>
                  </div>
                  <div className="flex-1 overflow-y-auto text-[11px] text-slate-900 font-mono whitespace-pre-wrap leading-relaxed shadow-inner bg-white p-3 rounded-lg border border-emerald-200">
                    <LinkifiedText text={viewVersion.markdown_content || 'No content generated.'} />
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto bg-slate-50 border border-emerald-100 rounded-xl p-5 text-xs text-slate-800 font-mono whitespace-pre-wrap leading-relaxed shadow-inner">
                <LinkifiedText text={viewVersion.markdown_content || 'No content generated.'} />
              </div>
            )}

            <div className="pt-4 border-t border-emerald-100 flex justify-between items-center flex-shrink-0 mt-4">
              <div className="flex space-x-2">
                <button
                  onClick={() => {
                    if (viewVersion.markdown_content) {
                      navigator.clipboard.writeText(viewVersion.markdown_content);
                      alert('Tailored resume Markdown copied to clipboard!');
                    }
                  }}
                  className="btn-secondary py-2 px-3 text-xs font-bold"
                >
                  📋 Copy Content
                </button>
                <button
                  onClick={() => {
                    if (viewVersion.markdown_content) {
                      handlePrintPdf(viewVersion.markdown_content, viewVersion.label || 'Tailored_Resume');
                    }
                  }}
                  className="py-2 px-3 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 rounded-xl text-xs font-bold transition-colors flex items-center shadow-xs"
                >
                  <Printer className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                  Export / Print PDF
                </button>
              </div>
              <div className="flex space-x-2">
                <button onClick={() => { setViewVersion(null); setCompareMode(false); }} className="btn-secondary py-2 px-4 text-xs">
                  Close
                </button>
                <Link href="/dashboard/outreach" className="btn-primary py-2 px-4 text-xs flex items-center">
                  <Send className="w-3.5 h-3.5 mr-1.5" />
                  Go to Outreach Mail &rarr;
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Uploaded Resume Modal */}
      {deletingResume && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-rose-500" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Delete Base Resume?</h3>
              <p className="text-sm text-slate-600 mb-6">
                Are you sure you want to delete <strong className="text-slate-800">{deletingResume.original_filename}</strong>? This action erases the file from storage.
              </p>

              <div className="flex space-x-3">
                <button
                  onClick={() => setDeletingResume(null)}
                  disabled={deleteLoading}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteResume}
                  disabled={deleteLoading}
                  className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-xl text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 transition-colors disabled:opacity-50"
                >
                  {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Delete Resume
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Tailored Version Modal */}
      {deletingVersion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-rose-500" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Delete AI Tailored Version?</h3>
              <p className="text-sm text-slate-600 mb-6">
                Delete <strong className="text-slate-800">{deletingVersion.label || `Version v${deletingVersion.version_number}`}</strong>?
              </p>

              <div className="flex space-x-3">
                <button
                  onClick={() => setDeletingVersion(null)}
                  disabled={deleteLoading}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteVersion}
                  disabled={deleteLoading}
                  className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-xl text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 transition-colors disabled:opacity-50"
                >
                  {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Delete Version
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Delete Modal */}
      {isConfirmBulkDeleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-rose-500" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Delete Selected Items?</h3>
              <p className="text-sm text-slate-600 mb-6">
                Are you sure you want to delete <strong className="text-rose-600">{activeTab === 'uploaded' ? selectedUploadedIds.length : selectedTailoredIds.length}</strong> selected {activeTab === 'uploaded' ? 'uploaded resumes' : 'tailored resume versions'}?
              </p>

              <div className="flex space-x-3">
                <button
                  onClick={() => setIsConfirmBulkDeleteOpen(false)}
                  disabled={deleteLoading}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkDelete}
                  disabled={deleteLoading}
                  className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-xl text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 transition-colors disabled:opacity-50"
                >
                  {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Delete Selected
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete All Modal */}
      {isConfirmDeleteAllOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-rose-500" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">
                Delete ALL {activeTab === 'uploaded' ? 'Uploaded Resumes' : 'Tailored Resume Versions'}?
              </h3>
              <p className="text-sm text-slate-600 mb-6">
                ⚠️ WARNING: This will permanently erase <strong className="text-rose-600">ALL {activeTab === 'uploaded' ? resumes.length : tailoredVersions.length}</strong> items in this category! This action cannot be undone.
              </p>

              <div className="flex space-x-3">
                <button
                  onClick={() => setIsConfirmDeleteAllOpen(false)}
                  disabled={deleteLoading}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteAll}
                  disabled={deleteLoading}
                  className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-xl text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 transition-colors disabled:opacity-50"
                >
                  {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Clear All
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
