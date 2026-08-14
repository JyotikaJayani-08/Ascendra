'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { Session, User } from '@supabase/supabase-js';
import { useRouter } from 'next/navigation';
import { API_BASE_URL } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      
      // Store token in localStorage for FastAPI backend compatibility
      if (session?.access_token) {
        localStorage.setItem('access_token', session.access_token);
      } else {
        localStorage.removeItem('access_token');
      }
      
      setLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      
      if (session?.access_token) {
        localStorage.setItem('access_token', session.access_token);
      } else {
        localStorage.removeItem('access_token');
      }
      
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const [toast, setToast] = useState<{ title: string; message: string } | null>(null);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    
    if (session?.access_token) {
      const url = `${API_BASE_URL}/notifications/stream?token=${session.access_token}`;
      eventSource = new EventSource(url);
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type !== 'ping') {
            setToast({ title: data.title || 'New Notification', message: data.message || '' });
            setTimeout(() => setToast(null), 5000);
          }
        } catch (e) {
          console.error('Failed to parse SSE message:', e);
        }
      };
      
      eventSource.onerror = () => {
        console.error('SSE Error, reconnecting...');
        // EventSource automatically tries to reconnect
      };
    }
    
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [session?.access_token]);

  const logout = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem('access_token');
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, session, loading, logout }}>
      {children}
      {/* Toast Notification UI */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 bg-white border border-emerald-200 shadow-xl rounded-xl p-4 w-80 animate-in slide-in-from-bottom-5 fade-in duration-300 flex items-start">
          <div className="flex-1">
            <h4 className="font-bold text-emerald-950 text-sm mb-1">{toast.title}</h4>
            <p className="text-xs text-emerald-900/70">{toast.message}</p>
          </div>
          <button onClick={() => setToast(null)} className="ml-4 text-emerald-900/40 hover:text-emerald-900">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
