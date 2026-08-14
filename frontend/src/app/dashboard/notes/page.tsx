'use client';

import { useState, useEffect } from 'react';
import { StickyNote, Plus, Loader2, Trash2, Edit2, X, Save, Sparkles, AlertTriangle } from 'lucide-react';
import { fetchApi } from '@/lib/api';

interface Note {
  id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [currentNote, setCurrentNote] = useState<{ id?: string, title: string, content: string }>({ title: '', content: '' });

  // Delete modal state
  const [deletingNote, setDeletingNote] = useState<Note | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    loadNotes();
  }, []);

  const loadNotes = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchApi('/notes');
      const items = data.items || data || [];
      setNotes(items);
    } catch (err: any) {
      console.error('Failed to load notes:', err);
      setError('Could not load notes. Please check your connection and try again.');
      setNotes([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (currentNote.id) {
        await fetchApi(`/notes/${currentNote.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ title: currentNote.title, content: currentNote.content })
        });
        setNotes(prev => prev.map(n => n.id === currentNote.id ? { ...n, title: currentNote.title, content: currentNote.content, updated_at: new Date().toISOString() } : n));
      } else {
        const created = await fetchApi('/notes', {
          method: 'POST',
          body: JSON.stringify({ title: currentNote.title, content: currentNote.content })
        });
        setNotes(prev => [created, ...prev]);
      }
      setIsModalOpen(false);
    } catch (err: any) {
      setError(err.message || 'Failed to save note. Please try again.');
      setTimeout(() => setError(null), 5000);
      setIsModalOpen(false);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deletingNote) return;
    setDeleteLoading(true);
    try {
      await fetchApi(`/notes/${deletingNote.id}`, { method: 'DELETE' });
    } catch (err: any) {
      console.error('Failed to delete note from backend:', err);
    }
    setNotes(prev => prev.filter(n => n.id !== deletingNote.id));
    setDeletingNote(null);
    setDeleteLoading(false);
  };

  const openNewNote = () => {
    setCurrentNote({ title: '', content: '' });
    setIsModalOpen(true);
  };

  const openEditNote = (note: Note) => {
    setCurrentNote(note);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-emerald-950 mb-1">Interview Prep & Notes</h2>
          <p className="text-emerald-900/70 font-medium">Keep thoughts, company research, and salary negotiation points.</p>
        </div>
        
        <button
          onClick={openNewNote}
          className="btn-primary flex items-center shadow-md shadow-emerald-500/20 text-sm"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Note
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-600 p-4 rounded-xl text-sm font-semibold">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {notes.map(note => (
            <div key={note.id} className="group relative glass-card p-6 flex flex-col justify-between h-64">
              <div>
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-base font-extrabold text-emerald-950 line-clamp-1 flex-1 pr-2">{note.title}</h3>
                  <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => openEditNote(note)} className="p-1.5 text-emerald-600 hover:text-emerald-800 bg-emerald-50 rounded-lg transition-colors">
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={() => setDeletingNote(note)} className="p-1.5 text-rose-500 hover:text-rose-700 bg-rose-50 rounded-lg transition-colors">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                
                <div className="overflow-hidden relative max-h-36">
                  <p className="text-emerald-900/80 text-xs font-medium whitespace-pre-wrap leading-relaxed">
                    {note.content}
                  </p>
                </div>
              </div>
              
              <div className="pt-3 border-t border-emerald-100 text-[11px] text-emerald-800/60 font-semibold">
                Updated {new Date(note.updated_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Note Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="glass-panel w-full max-w-lg p-6 bg-white border border-emerald-100 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center pb-4 border-b border-emerald-100 mb-4">
              <h3 className="text-base font-extrabold text-emerald-950 flex items-center">
                <StickyNote className="w-5 h-5 mr-2 text-emerald-600" />
                {currentNote.id ? 'Edit Note' : 'New Prep Note'}
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={currentNote.title}
                  onChange={(e) => setCurrentNote({...currentNote, title: e.target.value})}
                  className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-sm text-slate-900 font-bold focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                  placeholder="e.g. System Design Questions"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Content</label>
                <textarea
                  required
                  rows={5}
                  value={currentNote.content}
                  onChange={(e) => setCurrentNote({...currentNote, content: e.target.value})}
                  className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-3 text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 leading-relaxed"
                  placeholder="Enter details..."
                />
              </div>
              
              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="btn-primary text-xs flex items-center"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Save className="w-4 h-4 mr-1" />}
                  Save Note
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingNote && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
          <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-rose-500" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">Delete Note?</h3>
              <p className="text-sm text-slate-600 mb-6">
                Are you sure you want to delete <strong className="text-slate-800">{deletingNote.title}</strong>? This action cannot be undone.
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => setDeletingNote(null)}
                  disabled={deleteLoading}
                  className="flex-1 py-2.5 px-4 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleteLoading}
                  className="flex-1 flex justify-center items-center py-2.5 px-4 rounded-xl text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 transition-colors disabled:opacity-50"
                >
                  {deleteLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  Delete Note
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
