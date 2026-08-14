'use client';

import { useState, useEffect } from 'react';
import { Briefcase, Loader2, Search, Plus, MapPin, Building, Globe, Wand2, X, Sparkles, RefreshCw, ExternalLink, Trash2, AlertTriangle, DollarSign, FileText } from 'lucide-react';
import { fetchApi } from '@/lib/api';
import { useJobs, Job } from '@/contexts/JobsContext';
import JobFilterBar, { type JobFilterValues } from '@/components/jobs/JobFilterBar';
import LinkifiedText from '@/components/common/LinkifiedText';

interface Resume {
  id: string;
  original_filename: string;
  status: string;
}

export default function JobsPage() {
  const { jobs, loading, syncing, syncProviderJobs, addManualJob, fetchJobs } = useJobs();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [remoteFilter, setRemoteFilter] = useState('ALL');
  const [isAdding, setIsAdding] = useState(false);
  const [newJob, setNewJob] = useState({ title: '', company_name: '', location: '', remote_status: 'REMOTE', source_url: '' });

  // Active filter values from JobFilterBar
  const [activeFilters, setActiveFilters] = useState<JobFilterValues>({
    query: '',
    location: 'Bengaluru, India',
    company: '',
    jobType: 'ALL',
    workMode: 'ALL',
    experience: 'ALL',
    provider: 'serpapi',
  });

  // Sync params
  const [syncWhat, setSyncWhat] = useState('');
  const [syncWhere, setSyncWhere] = useState('');

  // AI Modal State
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuccess, setAiSuccess] = useState<string | null>(null);
  const [tailoringStyle, setTailoringStyle] = useState('ats_optimized');
  const [customInstructions, setCustomInstructions] = useState('');

  // Job Detail Modal
  const [detailJob, setDetailJob] = useState<Job | null>(null);

  // Delete Job State
  const [deletingJob, setDeletingJob] = useState<Job | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const handleAddJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAdding(true);
    setError(null);
    setSuccess(null);
    try {
      await addManualJob(newJob);
      setNewJob({ title: '', company_name: '', location: '', remote_status: 'REMOTE', source_url: '' });
      setSuccess('Job saved successfully!');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err?.message || 'Failed to save job. Please try again.');
    } finally {
      setIsAdding(false);
    }
  };

  const handleSyncAllJobs = async () => {
    try {
      setError(null);
      setSuccess('Syncing jobs from all providers (SerpApi, RemoteOK, WeWorkRemotely)...');
      await Promise.all([
        syncProviderJobs('serpapi', syncWhat || undefined, syncWhere || undefined).catch(() => null),
        syncProviderJobs('remoteok', syncWhat || undefined).catch(() => null),
        syncProviderJobs('weworkremotely', syncWhat || undefined).catch(() => null),
      ]);
      setSuccess('Successfully synced jobs from all providers!');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to sync jobs from some providers.');
      setTimeout(() => setError(null), 3000);
    }
  };

  useEffect(() => {
    // Pre-fetch resumes so AI tailor modal has data ready immediately
    fetchApi('/resumes')
      .then(res => {
        const items = Array.isArray(res) ? res : (res?.items || []);
        setResumes(items);
        if (items.length > 0) setSelectedResumeId(items[0].id);
      })
      .catch(() => setResumes([]));
  }, []);

  const openAiModal = async (job: Job) => {
    setSelectedJob(job);
    setIsAiModalOpen(true);
    setAiSuccess(null);
    try {
      const res = await fetchApi('/resumes');
      const items = Array.isArray(res) ? res : (res?.items || []);
      setResumes(items);
      if (items.length > 0) {
        setSelectedResumeId(prev => prev || items[0].id);
      } else {
        setSelectedResumeId('');
      }
    } catch (err) {
      console.error('Failed to load resumes for AI tailor:', err);
    }
  };

  const handleGenerateResume = async () => {
    if (!selectedResumeId || !selectedJob) return;
    setAiLoading(true);
    setAiSuccess(null);
    try {
      await fetchApi('/ai/resume/generate', {
        method: 'POST',
        body: JSON.stringify({
          resume_id: selectedResumeId,
          job_id: selectedJob.id,
          label: `AI Optimized for ${selectedJob.company?.name || selectedJob.company_name || 'Job'}`,
          tailoring_style: tailoringStyle,
          custom_instructions: customInstructions || undefined,
        })
      });
      setAiSuccess("Resume tailored & version saved in Resume Vault!");
    } catch (err: any) {
      setAiSuccess(null);
      setError(err.message || 'AI resume generation failed. Please try again.');
      setTimeout(() => setError(null), 5000);
    } finally {
      setAiLoading(false);
    }
  };

  const filteredJobs = jobs.filter(j => {
    // Text search — title + company
    const matchesSearch = !searchQuery || 
      j.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
      (j.company?.name || j.company_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (j.description || '').toLowerCase().includes(searchQuery.toLowerCase());

    // Work mode filter
    const matchesWorkMode = activeFilters.workMode === 'ALL' || 
      (j.remote_status || 'UNKNOWN').toUpperCase() === activeFilters.workMode;

    // Job type / employment type filter
    const jobTypeMap: Record<string, string[]> = {
      'fulltime': ['FULL_TIME', 'FULLTIME'],
      'contract': ['CONTRACT', 'FREELANCE', 'TEMP'],
      'internship': ['INTERNSHIP', 'INTERN'],
    };
    const matchesJobType = activeFilters.jobType === 'ALL' || 
      (jobTypeMap[activeFilters.jobType] || []).includes((j.employment_type || 'UNKNOWN').toUpperCase());

    // Experience level filter
    const expMap: Record<string, string[]> = {
      '0-2 years': ['ENTRY', 'JUNIOR', 'INTERN', 'INTERNSHIP'],
      '2-5 years': ['MID', 'MID_LEVEL'],
      '5+ years': ['SENIOR', 'LEAD', 'EXECUTIVE', 'PRINCIPAL', 'DIRECTOR'],
    };
    const matchesExperience = activeFilters.experience === 'ALL' || 
      (expMap[activeFilters.experience] || []).includes((j.experience_level || 'UNKNOWN').toUpperCase());

    // Company name filter
    const matchesCompany = !activeFilters.company || 
      (j.company?.name || j.company_name || '').toLowerCase().includes(activeFilters.company.toLowerCase());

    return matchesSearch && matchesWorkMode && matchesJobType && matchesExperience && matchesCompany;
  });

  const handleDeleteJob = async () => {
    if (!deletingJob) return;
    setDeleteLoading(true);
    try {
      await fetchApi(`/jobs/${deletingJob.id}`, { method: 'DELETE' });
      setSuccess('Job removed!');
      setTimeout(() => setSuccess(null), 3000);
      setDeletingJob(null);
      await fetchJobs();
    } catch (err: any) {
      setError(err.message || 'Failed to delete job.');
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      {/* Informative Header Banner + Disclaimer */}
      <div className="bg-gradient-to-r from-emerald-900/90 to-teal-900/90 text-white p-5 rounded-2xl shadow-md border border-emerald-700/50">
        <div className="flex items-start space-x-3">
          <div className="p-2 bg-emerald-500/20 rounded-xl mt-0.5">
            <Sparkles className="w-5 h-5 text-emerald-300" />
          </div>
          <div>
            <h3 className="font-bold text-base text-emerald-100">Target Jobs Hub & AI Tailoring</h3>
            <p className="text-xs text-emerald-200/80 mt-1 leading-relaxed">
              Track open job opportunities from <strong>LinkedIn, Glassdoor, or Company Portals</strong> (or sync live remote roles). Once saved here, click <strong>&ldquo;Tailor Resume with AI&rdquo;</strong> to automatically generate ATS-optimized resumes and targeted recruiter cold emails for that specific position.
            </p>
          </div>
        </div>
      </div>

      {/* Professional Cold Email Disclaimer */}
      <div className="bg-amber-50/80 border border-amber-200/80 p-4 rounded-xl flex items-start gap-3">
        <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
        <p className="text-xs text-amber-900/80 leading-relaxed">
          <strong>Disclaimer:</strong> This platform is a recruiter cold-email outreach tool — not a job application portal. Ascendra helps you craft and send personalized cold emails directly to recruiters and hiring contacts whose information is publicly available. To formally apply for a position through the company&apos;s official careers page, use the <strong>&ldquo;View Original Posting&rdquo;</strong> link on each job card.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-emerald-950 mb-1">Target Jobs Hub</h2>
          <p className="text-emerald-900/70 font-medium">Instahyre-grade search, Google Jobs live sync, and AI resume tailoring.</p>
        </div>
      </div>

      {/* Instahyre-Grade Job Filter Bar with Live Provider Sync */}
      <JobFilterBar
        initialValues={activeFilters}
        onApplyFilters={(vals) => {
          setActiveFilters(vals);
          setSearchQuery(vals.query);
        }}
        onSyncProvider={async (provider, vals) => {
          try {
            setError(null);
            setSuccess(`Syncing live jobs from ${provider.toUpperCase()} (${vals.query || 'Tech'} in ${vals.location || 'India'})...`);
            await syncProviderJobs(provider, vals.query, vals.location);
            setSuccess(`Live jobs updated from ${provider.toUpperCase()}!`);
            setTimeout(() => setSuccess(null), 4000);
          } catch (err: any) {
            setError(err.message || `Failed to sync from ${provider}`);
          }
        }}
        syncing={syncing}
      />

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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Track job form */}
        <div className="lg:col-span-1">
          <form onSubmit={handleAddJob} className="glass-panel p-6">
            <h3 className="text-lg font-extrabold text-emerald-950 mb-1 flex items-center">
              <Plus className="w-5 h-5 mr-2 text-emerald-600" />
              Track Target Job
            </h3>
            <p className="text-xs text-emerald-800/80 font-medium mb-4">
              Add any job you found on LinkedIn, Indeed, or career sites to run AI resume optimization.
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Job Title</label>
                <input
                  required
                  type="text"
                  value={newJob.title}
                  onChange={e => setNewJob({...newJob, title: e.target.value})}
                  className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                  placeholder="e.g. Senior Frontend Engineer"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Company Name</label>
                <input
                  required
                  type="text"
                  value={newJob.company_name}
                  onChange={e => setNewJob({...newJob, company_name: e.target.value})}
                  className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                  placeholder="e.g. Stripe"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Location</label>
                  <input
                    type="text"
                    value={newJob.location}
                    onChange={e => setNewJob({...newJob, location: e.target.value})}
                    className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                    placeholder="e.g. San Francisco"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Type</label>
                  <select
                    value={newJob.remote_status}
                    onChange={e => setNewJob({...newJob, remote_status: e.target.value})}
                    className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                  >
                    <option value="REMOTE">Remote</option>
                    <option value="HYBRID">Hybrid</option>
                    <option value="ONSITE">On-site</option>
                  </select>
                </div>
              </div>
              
              <button
                type="submit"
                disabled={isAdding}
                className="w-full btn-primary py-3 text-sm flex justify-center items-center mt-2"
              >
                {isAdding ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Save Job Opportunity'}
              </button>
            </div>
          </form>
        </div>

        {/* Job cards list */}
        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="glass-panel p-12 text-center">
              <Briefcase className="h-12 w-12 text-emerald-500 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-emerald-950 mb-1">No jobs saved</h3>
              <p className="text-sm text-emerald-800/70">Track a job on the left to start generating tailored AI resumes.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredJobs.map((job) => (
                <div key={job.id} className="glass-card p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <h4
                        onClick={() => setDetailJob(job)}
                        className="text-base font-bold text-emerald-950 hover:text-emerald-600 transition-colors line-clamp-1 cursor-pointer"
                      >
                        {job.title}
                      </h4>
                      <div className="flex items-center gap-1.5">
                        <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {job.remote_status || 'REMOTE'}
                        </span>
                        <button
                          onClick={(e) => { e.stopPropagation(); setDeletingJob(job); }}
                          className="p-1 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-colors"
                          title="Delete job"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    
                    <div className="space-y-1.5 text-xs text-emerald-900/70 font-medium mb-3">
                      <div className="flex items-center text-emerald-950 font-semibold">
                        <Building className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                        {job.company?.name || job.company_name || 'Unknown Company'}
                      </div>
                      <div className="flex items-center">
                        <MapPin className="w-3.5 h-3.5 mr-1.5 text-emerald-500" />
                        {job.location || 'Remote'}
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    {job.source_url && (
                      <a
                        href={job.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="w-full py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-bold transition-all flex items-center justify-center"
                      >
                        <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
                        View Original Posting
                      </a>
                    )}
                    <button
                      onClick={() => openAiModal(job)}
                      className="w-full py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center shadow-md shadow-emerald-500/20"
                    >
                      <Sparkles className="w-4 h-4 mr-1.5" />
                      Tailor Resume with AI
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* AI Generate Modal */}
      {isAiModalOpen && selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="glass-panel w-full max-w-md p-6 bg-white border border-emerald-100 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center pb-4 border-b border-emerald-100 mb-4">
              <h3 className="text-base font-extrabold text-emerald-950 flex items-center">
                <Sparkles className="w-5 h-5 mr-2 text-emerald-600" />
                AI Resume Tailor
              </h3>
              <button onClick={() => setIsAiModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <p className="text-xs text-emerald-900/80 leading-relaxed">
                Generate an optimized resume tailored for <strong className="text-emerald-950">{selectedJob.title}</strong> at <strong className="text-emerald-950">{selectedJob.company?.name || selectedJob.company_name}</strong>.
              </p>
              
              {aiSuccess ? (
                <div className="space-y-4">
                  <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-4 rounded-xl text-center text-xs font-bold">
                    ✅ {aiSuccess}
                  </div>
                  <div className="flex space-x-2">
                    <a
                      href="/dashboard/resumes"
                      className="flex-1 py-2.5 px-3 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-bold transition-colors flex items-center justify-center"
                    >
                      <FileText className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                      Resume Vault
                    </a>
                    <a
                      href="/dashboard/outreach"
                      className="flex-1 py-2.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-colors flex items-center justify-center shadow-md shadow-emerald-500/20"
                    >
                      <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-300" />
                      Outreach Mail ✉️
                    </a>
                  </div>
                </div>
              ) : (
                <>
                  {resumes.length === 0 ? (
                    <div className="text-center py-6 space-y-3">
                      <div className="w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center mx-auto">
                        <FileText className="w-6 h-6 text-amber-500" />
                      </div>
                      <div>
                        <p className="text-sm font-bold text-slate-800">No Resume Uploaded</p>
                        <p className="text-xs text-slate-500 mt-1">Upload a resume in the Resume Vault first, then come back to tailor it for this job.</p>
                      </div>
                      <a
                        href="/dashboard/resumes"
                        className="inline-flex items-center px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-colors shadow-md shadow-emerald-500/20"
                      >
                        <FileText className="w-3.5 h-3.5 mr-1.5" />
                        Go to Resume Vault
                      </a>
                    </div>
                  ) : (
                    <>
                      <div>
                        <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2">Select Base Resume</label>
                        <select
                          value={selectedResumeId}
                          onChange={(e) => setSelectedResumeId(e.target.value)}
                          className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-3 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                        >
                          {resumes.map(r => (
                            <option key={r.id} value={r.id}>{r.original_filename}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2">Tailoring Style</label>
                        <select
                          value={tailoringStyle}
                          onChange={(e) => setTailoringStyle(e.target.value)}
                          className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-3 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                        >
                          <option value="ats_optimized">🎯 ATS Optimized — Maximum keyword match</option>
                          <option value="narrative">📖 Narrative — Storytelling approach</option>
                          <option value="skills_focused">⚡ Skills Focused — Technical skills prominence</option>
                          <option value="experience_focused">💼 Experience Focused — Deep work history</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2">Custom Instructions <span className="text-emerald-600/60 normal-case font-medium">(optional)</span></label>
                        <textarea
                          value={customInstructions}
                          onChange={(e) => setCustomInstructions(e.target.value)}
                          placeholder="e.g. Emphasize leadership experience, highlight cloud certifications..."
                          maxLength={500}
                          rows={2}
                          className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-xs text-slate-900 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors resize-none placeholder-slate-400"
                        />
                      </div>

                      <button
                        onClick={handleGenerateResume}
                        disabled={aiLoading || !selectedResumeId}
                        className="w-full btn-primary py-3 text-xs flex justify-center items-center mt-4"
                      >
                        {aiLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate AI Version ✨'}
                      </button>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Job Detail Modal */}
      {detailJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="glass-panel w-full max-w-lg p-6 bg-white border border-emerald-100 shadow-2xl animate-in zoom-in-95 duration-200 max-h-[85vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-4 border-b border-emerald-100 mb-4">
              <h3 className="text-base font-extrabold text-emerald-950 flex items-center">
                <Briefcase className="w-5 h-5 mr-2 text-emerald-600" />
                Job Details
              </h3>
              <button onClick={() => setDetailJob(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <h4 className="text-lg font-extrabold text-emerald-950">{detailJob.title}</h4>
                <p className="text-sm font-semibold text-emerald-700 mt-1">
                  {detailJob.company?.name || detailJob.company_name || 'Unknown Company'}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <MapPin className="w-3 h-3 mr-1" />
                  {detailJob.location || 'Remote'}
                </span>
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-teal-50 text-teal-700 border border-teal-200">
                  {detailJob.remote_status || 'REMOTE'}
                </span>
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {detailJob.employment_type || 'UNKNOWN'}
                </span>
              </div>

              {((detailJob as any).salary_min || (detailJob as any).salary_max) && (
                <div className="bg-emerald-50/60 border border-emerald-100 rounded-xl p-3">
                  <p className="text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1 flex items-center">
                    <DollarSign className="w-3.5 h-3.5 mr-1" />
                    Salary Range
                  </p>
                  <p className="text-sm font-bold text-emerald-950">
                    {(detailJob as any).salary_currency || 'USD'} {(detailJob as any).salary_min?.toLocaleString() || '—'} – {(detailJob as any).salary_max?.toLocaleString() || '—'}
                  </p>
                </div>
              )}

              {(detailJob as any).description && (
                <div>
                  <p className="text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2 flex items-center">
                    <FileText className="w-3.5 h-3.5 mr-1" />
                    Description
                  </p>
                  <div className="bg-slate-50 border border-emerald-100 rounded-xl p-3 text-xs text-slate-800 leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
                    <LinkifiedText text={(detailJob as any).description} />
                  </div>
                </div>
              )}

              {(detailJob as any).requirements && (
                <div>
                  <p className="text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2">Requirements</p>
                  <div className="bg-slate-50 border border-emerald-100 rounded-xl p-3 text-xs text-slate-800 leading-relaxed whitespace-pre-wrap max-h-36 overflow-y-auto">
                    <LinkifiedText text={(detailJob as any).requirements} />
                  </div>
                </div>
              )}

              {detailJob.source_url && (
                <a
                  href={detailJob.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-bold transition-all flex items-center justify-center"
                >
                  <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
                  View Original Job Posting
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Job Confirmation Modal */}
      {deletingJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-rose-500" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Remove Job?</h3>
              <p className="text-sm text-slate-600 mb-6">
                Remove <strong className="text-slate-800">{deletingJob.title}</strong> from your tracked jobs? This cannot be undone.
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => setDeletingJob(null)}
                  disabled={deleteLoading}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteJob}
                  disabled={deleteLoading}
                  className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-xl text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 transition-colors disabled:opacity-50"
                >
                  {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Delete Job
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
