'use client';

import { useState, useEffect } from 'react';
import { Search, Loader2, FileText, Briefcase, User, Send, Building2 } from 'lucide-react';
import { fetchApi } from '@/lib/api';
import { useRouter } from 'next/navigation';

export function CommandPalette({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  // Handle Cmd+K global shortcut
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        isOpen ? onClose() : (document.getElementById('cmd-k-btn')?.click()); // Hacky but works for the demo without moving state up too far
      }
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [isOpen, onClose]);

  // Deep Search Function
  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      return;
    }

    const searchAll = async () => {
      setLoading(true);
      try {
        const [jobs, resumes, contacts, apps] = await Promise.all([
          fetchApi('/jobs'),
          fetchApi('/resumes'),
          fetchApi('/contacts'),
          fetchApi('/applications')
        ]);
        
        const combined = [
          ...(jobs.items || jobs).map((j: any) => ({ ...j, _type: 'job' })),
          ...(resumes.items || resumes).map((r: any) => ({ ...r, _type: 'resume' })),
          ...(contacts.items || contacts).map((c: any) => ({ ...c, _type: 'contact' })),
          ...(apps.items || apps).map((a: any) => ({ ...a, _type: 'application' })),
        ];

        const filtered = combined.filter(item => {
          const searchStr = query.toLowerCase();
          if (item._type === 'job') return item.title.toLowerCase().includes(searchStr) || (item.company_name || '').toLowerCase().includes(searchStr);
          if (item._type === 'resume') return item.original_filename.toLowerCase().includes(searchStr);
          if (item._type === 'contact') return item.full_name.toLowerCase().includes(searchStr) || (item.job_title || '').toLowerCase().includes(searchStr);
          if (item._type === 'application') return (item.job_title_snapshot || '').toLowerCase().includes(searchStr);
          return false;
        });

        setResults(filtered.slice(0, 10)); // Top 10 results
      } catch (error) {
        console.error("Deep search failed", error);
      } finally {
        setLoading(false);
      }
    };

    const debounce = setTimeout(searchAll, 300);
    return () => clearTimeout(debounce);
  }, [query]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-32 sm:pt-48">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity" onClick={onClose} />
      
      {/* Dialog */}
      <div className="relative w-full max-w-2xl transform overflow-hidden rounded-2xl bg-slate-900/90 border border-slate-700/50 shadow-2xl transition-all">
        <div className="relative flex items-center p-4 border-b border-slate-800">
          <Search className="h-5 w-5 text-slate-400" />
          <input
            type="text"
            className="w-full bg-transparent border-0 pl-4 text-white focus:ring-0 placeholder-slate-500 text-lg outline-none"
            placeholder="Search everywhere..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          {loading && <Loader2 className="h-5 w-5 animate-spin text-blue-500" />}
          <div className="ml-2 text-xs text-slate-500 px-2 py-1 rounded bg-slate-800">ESC</div>
        </div>

        <div className="max-h-96 overflow-y-auto p-2">
          {query.length > 0 && results.length === 0 && !loading && (
            <div className="p-12 text-center text-slate-400">No results found for "{query}"</div>
          )}
          
          {query.length === 0 && (
            <div className="p-8 text-center text-slate-500 text-sm">
              Start typing to deep-search your Jobs, Resumes, and Contacts.
            </div>
          )}

          {results.map((result) => (
            <button
              key={`${result._type}-${result.id}`}
              onClick={() => {
                if (result._type === 'job') router.push('/dashboard/jobs');
                if (result._type === 'resume') router.push('/dashboard/resumes');
                if (result._type === 'contact' || result._type === 'application') router.push('/dashboard/outreach');
                onClose();
              }}
              className="w-full flex items-center px-4 py-3 hover:bg-slate-800/50 rounded-lg group transition-colors text-left"
            >
              <div className={`p-2 rounded-lg mr-4 ${
                result._type === 'job' ? 'bg-teal-500/10 text-teal-400' :
                result._type === 'resume' ? 'bg-emerald-500/10 text-emerald-400' :
                result._type === 'contact' ? 'bg-teal-500/10 text-teal-400' :
                'bg-emerald-500/10 text-emerald-400'
              }`}>
                {result._type === 'job' && <Briefcase className="w-5 h-5" />}
                {result._type === 'resume' && <FileText className="w-5 h-5" />}
                {result._type === 'contact' && <User className="w-5 h-5" />}
                {result._type === 'application' && <Send className="w-5 h-5" />}
              </div>
              
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-200 group-hover:text-white">
                  {result._type === 'job' && result.title}
                  {result._type === 'resume' && result.original_filename}
                  {result._type === 'contact' && result.full_name}
                  {result._type === 'application' && result.job_title_snapshot}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {result._type === 'job' && (result.company?.name || result.company_name)}
                  {result._type === 'resume' && `${(result.file_size_bytes / 1024).toFixed(1)} KB`}
                  {result._type === 'contact' && result.job_title}
                  {result._type === 'application' && result.company_name_snapshot}
                </p>
              </div>
              
              <div className="text-xs text-slate-500 font-medium px-2 py-1 rounded bg-slate-800/50 uppercase tracking-wider">
                {result._type}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
