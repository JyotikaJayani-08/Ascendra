'use client';

import React, { useState } from 'react';
import { Search, MapPin, Building2, Briefcase, Filter, X, RefreshCw, Sparkles, SlidersHorizontal, Globe } from 'lucide-react';

export interface JobFilterValues {
  query: string;
  location: string;
  company: string;
  jobType: string; // 'ALL' | 'fulltime' | 'contract' | 'internship'
  workMode: string; // 'ALL' | 'REMOTE' | 'ON_SITE'
  experience: string; // 'ALL' | '0-2 years' | '2-5 years' | '5+ years'
  provider: string; // 'serpapi' | 'remotive' | 'jobicy'
}

interface JobFilterBarProps {
  initialValues?: Partial<JobFilterValues>;
  onApplyFilters: (filters: JobFilterValues) => void;
  onSyncProvider?: (provider: string, filters: JobFilterValues) => void;
  loading?: boolean;
  syncing?: boolean;
}

export default function JobFilterBar({
  initialValues,
  onApplyFilters,
  onSyncProvider,
  loading = false,
  syncing = false,
}: JobFilterBarProps) {
  const [filters, setFilters] = useState<JobFilterValues>({
    query: initialValues?.query || '',
    location: initialValues?.location || 'Bengaluru, India',
    company: initialValues?.company || '',
    jobType: initialValues?.jobType || 'ALL',
    workMode: initialValues?.workMode || 'ALL',
    experience: initialValues?.experience || 'ALL',
    provider: initialValues?.provider || 'serpapi',
  });

  const [isExpanded, setIsExpanded] = useState(false);

  const handleInputChange = (field: keyof JobFilterValues, value: string) => {
    const updated = { ...filters, [field]: value };
    setFilters(updated);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onApplyFilters(filters);
  };

  const handleReset = () => {
    const resetVals: JobFilterValues = {
      query: '',
      location: 'India',
      company: '',
      jobType: 'ALL',
      workMode: 'ALL',
      experience: 'ALL',
      provider: 'serpapi',
    };
    setFilters(resetVals);
    onApplyFilters(resetVals);
  };

  return (
    <div className="glass-panel p-5 border border-emerald-100 shadow-md rounded-2xl space-y-4 transition-all">
      {/* Primary Top Bar */}
      <form onSubmit={handleSearchSubmit} className="flex flex-col lg:flex-row items-stretch lg:items-center gap-3">
        {/* Role & Skills Search */}
        <div className="relative flex-1 min-w-[240px]">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-emerald-600/70">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            placeholder="Enter title or skills (e.g. Python, FastAPI, React)..."
            value={filters.query}
            onChange={(e) => handleInputChange('query', e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-50/80 border border-emerald-200/80 rounded-xl text-xs font-semibold text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-xs"
          />
        </div>

        {/* Location Filter */}
        <div className="relative w-full lg:w-56">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-emerald-600/70">
            <MapPin className="w-4 h-4" />
          </div>
          <input
            type="text"
            placeholder="Location (e.g. Bengaluru, Remote)"
            value={filters.location}
            onChange={(e) => handleInputChange('location', e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-50/80 border border-emerald-200/80 rounded-xl text-xs font-semibold text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-xs"
          />
        </div>

        {/* Provider Dropdown */}
        <div className="w-full lg:w-48">
          <select
            value={filters.provider}
            onChange={(e) => handleInputChange('provider', e.target.value)}
            className="w-full px-3 py-2.5 bg-emerald-50/90 border border-emerald-300 rounded-xl text-xs font-bold text-emerald-950 focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-xs"
          >
            <option value="serpapi">🌐 Google Jobs (SerpApi)</option>
            <option value="remotive">🚀 Remotive (Free)</option>
            <option value="jobicy">🎯 Jobicy (Free)</option>
          </select>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="submit"
            className="btn-primary py-2.5 px-4 text-xs flex items-center justify-center font-bold shadow-sm flex-1 lg:flex-none"
          >
            <Search className="w-3.5 h-3.5 mr-1.5" />
            Search
          </button>

          {onSyncProvider && (
            <button
              type="button"
              onClick={() => onSyncProvider(filters.provider, filters)}
              disabled={syncing}
              className="py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-emerald-500/20 flex items-center justify-center disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${syncing ? 'animate-spin' : ''}`} />
              Live Sync
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className={`p-2.5 border rounded-xl transition-all ${
              isExpanded
                ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
            title="Toggle Instahyre Filters"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>
        </div>
      </form>

      {/* Instahyre-Grade Advanced Drawer */}
      {isExpanded && (
        <div className="pt-4 border-t border-emerald-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-in fade-in zoom-in-95 duration-200">
          {/* Company Name */}
          <div>
            <label className="block text-[11px] font-bold text-emerald-900 uppercase tracking-wider mb-1 flex items-center">
              <Building2 className="w-3 h-3 mr-1 text-emerald-600" />
              Target Company
            </label>
            <input
              type="text"
              placeholder="e.g. Razorpay, Amazon, TCS"
              value={filters.company}
              onChange={(e) => handleInputChange('company', e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-emerald-200/80 rounded-xl text-xs text-slate-800 focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          {/* Job Type */}
          <div>
            <label className="block text-[11px] font-bold text-emerald-900 uppercase tracking-wider mb-1 flex items-center">
              <Briefcase className="w-3 h-3 mr-1 text-emerald-600" />
              Job Type
            </label>
            <select
              value={filters.jobType}
              onChange={(e) => handleInputChange('jobType', e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-emerald-200/80 rounded-xl text-xs text-slate-800 focus:ring-1 focus:ring-emerald-500"
            >
              <option value="ALL">Both Full-time & Internship</option>
              <option value="fulltime">Full-time Only</option>
              <option value="contract">Contract / Freelance</option>
              <option value="internship">Internship</option>
            </select>
          </div>

          {/* Work Mode / Remote */}
          <div>
            <label className="block text-[11px] font-bold text-emerald-900 uppercase tracking-wider mb-1 flex items-center">
              <Globe className="w-3 h-3 mr-1 text-emerald-600" />
              Work Mode
            </label>
            <select
              value={filters.workMode}
              onChange={(e) => handleInputChange('workMode', e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-emerald-200/80 rounded-xl text-xs text-slate-800 focus:ring-1 focus:ring-emerald-500"
            >
              <option value="ALL">All Modes (Remote & On-site)</option>
              <option value="REMOTE">Remote Only (Work From Home)</option>
              <option value="ON_SITE">On-site / Office</option>
            </select>
          </div>

          {/* Experience Level */}
          <div>
            <label className="block text-[11px] font-bold text-emerald-900 uppercase tracking-wider mb-1 flex items-center">
              <Sparkles className="w-3 h-3 mr-1 text-amber-500" />
              Experience Level
            </label>
            <select
              value={filters.experience}
              onChange={(e) => handleInputChange('experience', e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-emerald-200/80 rounded-xl text-xs text-slate-800 focus:ring-1 focus:ring-emerald-500"
            >
              <option value="ALL">All Experience Levels</option>
              <option value="0-2 years">0 - 2 years (Entry Level / Freshers)</option>
              <option value="2-5 years">2 - 5 years (Mid-Level)</option>
              <option value="5+ years">5+ years (Senior / Lead)</option>
            </select>
          </div>

          <div className="lg:col-span-4 flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={handleReset}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition-colors"
            >
              Reset All Filters
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
