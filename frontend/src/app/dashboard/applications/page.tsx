'use client';

import { useEffect, useState } from 'react';
import { Loader2, LayoutGrid, List as ListIcon, Building, Calendar, Plus, X, Sparkles, Trash2, AlertTriangle, FileText } from 'lucide-react';
import { fetchApi } from '@/lib/api';
import { useApplications, Application } from '@/contexts/ApplicationsContext';

const COLUMNS = [
  { id: 'DRAFT', label: 'Drafts', color: 'bg-slate-400' },
  { id: 'READY', label: 'Ready', color: 'bg-emerald-500' },
  { id: 'SENT', label: 'Sent', color: 'bg-teal-500' },
  { id: 'INTERVIEW', label: 'Interview', color: 'bg-emerald-600' },
  { id: 'OFFER', label: 'Offer', color: 'bg-teal-600' },
  { id: 'REJECTED', label: 'Rejected', color: 'bg-rose-500' },
];

// Client-side mirror of backend state machine (simplified for Kanban columns)
const ALLOWED_TRANSITIONS: Record<string, Set<string>> = {
  'DRAFT': new Set(['READY', 'ARCHIVED', 'WITHDRAWN']),
  'READY': new Set(['RESUME_GENERATED', 'DRAFT', 'ARCHIVED', 'WITHDRAWN']),
  'RESUME_GENERATED': new Set(['EMAIL_GENERATED', 'ARCHIVED', 'WITHDRAWN']),
  'EMAIL_GENERATED': new Set(['AWAITING_APPROVAL', 'ARCHIVED', 'WITHDRAWN']),
  'AWAITING_APPROVAL': new Set(['QUEUED', 'EMAIL_GENERATED', 'ARCHIVED', 'WITHDRAWN']),
  'QUEUED': new Set(['SENT', 'ARCHIVED']),
  'SENT': new Set(['DELIVERED', 'REPLY_RECEIVED', 'REJECTED', 'ARCHIVED']),
  'DELIVERED': new Set(['REPLY_RECEIVED', 'REJECTED', 'ARCHIVED']),
  'REPLY_RECEIVED': new Set(['INTERVIEW', 'REJECTED', 'ARCHIVED']),
  'INTERVIEW': new Set(['OFFER', 'REJECTED', 'ARCHIVED']),
  'OFFER': new Set(['ARCHIVED']),
  'REJECTED': new Set(['ARCHIVED']),
  'WITHDRAWN': new Set(['ARCHIVED']),
  'ARCHIVED': new Set(),
};

function canTransition(from: string, to: string): boolean {
  if (from === to) return false;
  return ALLOWED_TRANSITIONS[from.toUpperCase()]?.has(to.toUpperCase()) ?? false;
}

export default function ApplicationsPage() {
  const { applications, loading, createApplication, updateApplicationStatus, deleteApplication } = useApplications();
  const [view, setView] = useState<'board' | 'list'>('board');
  const [draggedAppId, setDraggedAppId] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Manage Modal State
  const [manageApp, setManageApp] = useState<Application | null>(null);

  // Delete State
  const [deletingApp, setDeletingApp] = useState<Application | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // New Application Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newCompany, setNewCompany] = useState('');
  const [creating, setCreating] = useState(false);

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newCompany) return;
    setCreating(true);

    try {
      const jobRes = await fetchApi('/jobs', {
        method: 'POST',
        body: JSON.stringify({
          title: newTitle,
          company_name: newCompany,
          remote_status: 'REMOTE',
        }),
      });

      await createApplication(jobRes.id);
      setIsModalOpen(false);
      setNewTitle('');
      setNewCompany('');
    } catch (err) {
      console.error('Failed to create application:', err);
      setIsModalOpen(false);
      setNewTitle('');
      setNewCompany('');
    } finally {
      setCreating(false);
    }
  };

  const handleDragStart = (e: React.DragEvent, appId: string) => {
    setDraggedAppId(appId);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e: React.DragEvent, newStatus: string) => {
    e.preventDefault();
    if (!draggedAppId || updatingId) return; // Debounce: reject if already updating

    const appToUpdate = applications.find(a => a.id === draggedAppId);
    if (!appToUpdate || appToUpdate.status === newStatus) {
      setDraggedAppId(null);
      return;
    }

    // Validate transition client-side
    if (!canTransition(appToUpdate.status, newStatus)) {
      setDraggedAppId(null);
      setError(`Cannot move from ${appToUpdate.status} to ${newStatus}. Invalid transition.`);
      setTimeout(() => setError(null), 4000);
      return;
    }

    setUpdatingId(draggedAppId);
    const idToUpdate = draggedAppId;
    setDraggedAppId(null);

    try {
      await updateApplicationStatus(idToUpdate, newStatus);
    } catch (error) {
      console.log('Transition failed, reverted by context');
    } finally {
      setUpdatingId(null);
    }
  };

  const openManageModal = (app: Application) => {
    setManageApp(app);
  };

  const handleDeleteApp = async () => {
    if (!deletingApp) return;
    setDeleteLoading(true);
    try {
      await deleteApplication(deletingApp.id);
      setSuccess('Application archived successfully.');
      setTimeout(() => setSuccess(null), 3000);
      setDeletingApp(null);
      setManageApp(null);
    } catch (err: any) {
      setError(err.message || 'Failed to delete application.');
    } finally {
      setDeleteLoading(false);
    }
  };

  if (loading && applications.length === 0) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out h-[calc(100vh-8rem)] flex flex-col">
      {/* Informative Header Banner */}
      <div className="bg-gradient-to-r from-emerald-900/90 to-teal-900/90 text-white p-4 rounded-2xl shadow-md border border-emerald-700/50 flex-shrink-0">
        <div className="flex items-start space-x-3">
          <div className="p-2 bg-emerald-500/20 rounded-xl mt-0.5">
            <Sparkles className="w-5 h-5 text-emerald-300" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-emerald-100">Recruitment Pipeline & Kanban Tracker</h3>
            <p className="text-xs text-emerald-200/80 mt-0.5 leading-relaxed">
              Track job applications across every recruitment stage. <strong>Drag & drop cards</strong> between stages (Draft → Sent → Interview → Offer) to update statuses. Moving applications automatically calculates your <strong>Funnel Velocity</strong> on the Dashboard!
            </p>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 flex-shrink-0">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-emerald-950 mb-1">Application Funnel</h2>
          <p className="text-emerald-900/70 font-medium">Drag & drop applications to manage your candidate pipeline.</p>
        </div>
        
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-primary flex items-center shadow-md shadow-emerald-500/20 text-sm"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Application
          </button>

          <div className="flex bg-emerald-100/60 p-1 rounded-xl border border-emerald-200/50 backdrop-blur-sm">
            <button
              onClick={() => setView('board')}
              className={`flex items-center px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                view === 'board' ? 'bg-white text-emerald-900 shadow-sm' : 'text-emerald-800/70 hover:text-emerald-950'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5 mr-1.5" />
              Board
            </button>
            <button
              onClick={() => setView('list')}
              className={`flex items-center px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                view === 'list' ? 'bg-white text-emerald-900 shadow-sm' : 'text-emerald-800/70 hover:text-emerald-950'
              }`}
            >
              <ListIcon className="w-3.5 h-3.5 mr-1.5" />
              List
            </button>
          </div>
        </div>
      </div>

      {/* Board View */}
      {view === 'board' ? (
        <div className="flex-1 overflow-x-auto pb-4">
          <div className="flex gap-5 min-w-max h-full">
            {COLUMNS.map(col => {
              const colApps = applications.filter(a => a.status === col.id);
              return (
                <div 
                  key={col.id} 
                  className="w-80 flex flex-col glass-panel p-4 border border-emerald-100/80"
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, col.id)}
                >
                  <div className="flex justify-between items-center mb-4 px-1">
                    <div className="flex items-center space-x-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${col.color}`} />
                      <h3 className="font-bold text-emerald-950 text-sm tracking-tight">{col.label}</h3>
                    </div>
                    <span className="bg-emerald-50 text-emerald-700 border border-emerald-200/80 text-xs py-0.5 px-2.5 rounded-full font-bold">
                      {colApps.length}
                    </span>
                  </div>
                  
                  <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                    {colApps.map(app => (
                      <div
                        key={app.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, app.id)}
                        onClick={() => openManageModal(app)}
                        className={`glass-card p-4 border ${
                          updatingId === app.id ? 'border-emerald-500 opacity-70 scale-95' : 'border-emerald-100/80 hover:border-emerald-300'
                        } cursor-grab active:cursor-grabbing transition-all group`}
                      >
                        <div className="flex justify-between items-start mb-1">
                          <h4 className="font-bold text-emerald-950 text-sm group-hover:text-emerald-600 transition-colors">
                            {app.job_title_snapshot || 'Software Engineer'}
                          </h4>
                          <button
                            onClick={(e) => { e.stopPropagation(); setDeletingApp(app); }}
                            className="p-1 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                            title="Delete"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                        <div className="flex items-center text-emerald-900/70 text-xs mb-3 font-medium">
                          <Building className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                          <span className="truncate">{app.company_name_snapshot || 'Company'}</span>
                        </div>
                        <div className="flex justify-between items-center text-[11px] text-emerald-800/60 font-medium">
                          <div className="flex items-center">
                            <Calendar className="w-3 h-3 mr-1" />
                            {new Date(app.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </div>
                          <span className="text-emerald-600 font-semibold group-hover:translate-x-0.5 transition-transform">
                            View &rarr;
                          </span>
                        </div>
                      </div>
                    ))}
                    {colApps.length === 0 && (
                      <div className="h-28 border-2 border-dashed border-emerald-200/80 rounded-xl flex items-center justify-center text-emerald-600/60 text-xs font-medium bg-white/40">
                        Drop application here
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* List View */
        <div className="glass-panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-emerald-900/70 uppercase bg-emerald-50/60 border-b border-emerald-100">
                <tr>
                  <th className="px-6 py-4 font-semibold">Role & Company</th>
                  <th className="px-6 py-4 font-semibold">Status</th>
                  <th className="px-6 py-4 font-semibold">Date Created</th>
                  <th className="px-6 py-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-emerald-50">
                {applications.map(app => (
                  <tr key={app.id} className="hover:bg-emerald-50/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-bold text-emerald-950">{app.job_title_snapshot || 'Software Engineer'}</div>
                      <div className="text-emerald-900/70 text-xs mt-0.5 flex items-center font-medium">
                        <Building className="w-3 h-3 mr-1 text-emerald-600" />
                        {app.company_name_snapshot || 'Company'}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {app.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-emerald-900/70 font-medium text-xs">
                      {new Date(app.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button
                        onClick={() => openManageModal(app)}
                        className="text-emerald-600 hover:text-emerald-800 text-xs font-bold transition-colors"
                      >
                        Manage
                      </button>
                      <button
                        onClick={() => setDeletingApp(app)}
                        className="text-rose-500 hover:text-rose-700 text-xs font-bold transition-colors"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* New Application Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="glass-panel w-full max-w-md p-6 bg-white border border-emerald-100 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-emerald-600" />
                <h3 className="text-lg font-extrabold text-emerald-950">Track New Application</h3>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateApplication} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Job Title</label>
                <input
                  required
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Senior AI Engineer"
                  className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Company Name</label>
                <input
                  required
                  type="text"
                  value={newCompany}
                  onChange={(e) => setNewCompany(e.target.value)}
                  placeholder="e.g. Anthropic"
                  className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>

              <button
                type="submit"
                disabled={creating}
                className="w-full btn-primary py-3 text-sm flex justify-center items-center mt-6"
              >
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create Application'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Manage Application Modal */}
      {manageApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="glass-panel w-full max-w-lg p-6 bg-white border border-emerald-100 shadow-2xl animate-in zoom-in-95 duration-200 max-h-[85vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-4 border-b border-emerald-100 mb-4">
              <h3 className="text-base font-extrabold text-emerald-950 flex items-center">
                <FileText className="w-5 h-5 mr-2 text-emerald-600" />
                Application Details
              </h3>
              <button onClick={() => setManageApp(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {error && (
              <div className="bg-rose-50 border border-rose-200 text-rose-600 p-3 rounded-xl text-xs font-semibold mb-4">
                {error}
              </div>
            )}
            {success && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-3 rounded-xl text-xs font-bold mb-4">
                ✅ {success}
              </div>
            )}

            <div className="space-y-5">
              {/* Job Info */}
              <div>
                <h4 className="text-lg font-extrabold text-emerald-950">{manageApp.job_title_snapshot || 'Untitled Role'}</h4>
                <p className="text-sm font-semibold text-emerald-700 mt-1 flex items-center">
                  <Building className="w-4 h-4 mr-1.5" />
                  {manageApp.company_name_snapshot || 'Unknown Company'}
                </p>
              </div>

              {/* Status + Transition */}
              <div>
                <p className="text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2">Current Status</p>
                <div className="flex flex-wrap gap-2">
                  {COLUMNS.map(col => {
                    const isCurrent = manageApp.status === col.id;
                    const isValid = canTransition(manageApp.status, col.id);
                    return (
                      <button
                        key={col.id}
                        disabled={!isValid && !isCurrent || updatingId === manageApp.id}
                        onClick={async () => {
                          if (isCurrent || !isValid || updatingId) return;
                          setUpdatingId(manageApp.id);
                          try {
                            await updateApplicationStatus(manageApp.id, col.id);
                            setManageApp(prev => prev ? { ...prev, status: col.id } : null);
                          } catch (err) {
                            setError('Failed to transition. Check allowed transitions.');
                            setTimeout(() => setError(null), 3000);
                          } finally {
                            setUpdatingId(null);
                          }
                        }}
                        className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
                          isCurrent
                            ? `${col.color} text-white border-transparent shadow-md`
                            : isValid
                            ? 'bg-white text-emerald-900/70 border-emerald-200 hover:border-emerald-400 hover:bg-emerald-50 cursor-pointer'
                            : 'bg-slate-50 text-slate-400 border-slate-100 cursor-not-allowed opacity-50'
                        }`}
                        title={!isValid && !isCurrent ? `Cannot transition from ${manageApp.status} to ${col.id}` : ''}
                      >
                        {updatingId === manageApp.id && !isCurrent && isValid ? '...' : col.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Notes */}
              <div>
                <p className="text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2">Notes</p>
                <div className="bg-slate-50 border border-emerald-100 rounded-xl p-3 text-xs text-slate-800 leading-relaxed min-h-[60px]">
                  {manageApp.notes || <span className="text-slate-400 italic">No notes added yet.</span>}
                </div>
              </div>

              {/* Dates */}
              <div className="flex gap-4 text-xs text-emerald-800/70 font-medium">
                <div className="flex items-center">
                  <Calendar className="w-3.5 h-3.5 mr-1.5" />
                  Created: {new Date(manageApp.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </div>
                <div className="flex items-center">
                  <Calendar className="w-3.5 h-3.5 mr-1.5" />
                  Updated: {new Date(manageApp.updated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </div>
              </div>

              {/* Actions */}
              <div className="flex space-x-3 pt-2 border-t border-emerald-100">
                <button
                  onClick={() => setManageApp(null)}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => { setDeletingApp(manageApp); }}
                  className="py-2.5 px-4 rounded-xl text-sm font-medium text-rose-600 hover:bg-rose-50 border border-rose-200 transition-colors flex items-center"
                >
                  <Trash2 className="w-4 h-4 mr-1.5" />
                  Archive
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Application Confirmation Modal */}
      {deletingApp && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-rose-500" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Archive Application?</h3>
              <p className="text-sm text-slate-600 mb-6">
                Archive <strong className="text-slate-800">{deletingApp.job_title_snapshot}</strong> at <strong className="text-slate-800">{deletingApp.company_name_snapshot}</strong>? This will remove it from your board.
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => setDeletingApp(null)}
                  disabled={deleteLoading}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteApp}
                  disabled={deleteLoading}
                  className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-xl text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 transition-colors disabled:opacity-50"
                >
                  {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Archive Application
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
