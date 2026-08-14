'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { fetchApi } from '@/lib/api';

export interface Application {
  id: string;
  job_id: string;
  status: string;
  notes: string | null;
  company_name_snapshot: string | null;
  job_title_snapshot: string | null;
  created_at: string;
  updated_at: string;
}

interface ApplicationsContextType {
  applications: Application[];
  loading: boolean;
  fetchApplications: () => Promise<void>;
  createApplication: (jobId: string) => Promise<void>;
  updateApplicationStatus: (id: string, status: string) => Promise<void>;
  deleteApplication: (id: string) => Promise<void>;
}

const ApplicationsContext = createContext<ApplicationsContextType | undefined>(undefined);

export function ApplicationsProvider({ children }: { children: ReactNode }) {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchApplications = async () => {
    setLoading(true);
    try {
      const data = await fetchApi('/applications?page_size=100');
      if (data && data.items) {
        setApplications(data.items);
      }
    } catch (error) {
      console.error('Failed to fetch applications:', error);
    } finally {
      setLoading(false);
    }
  };

  const createApplication = async (jobId: string) => {
    try {
      const res = await fetchApi('/applications', {
        method: 'POST',
        body: JSON.stringify({ job_id: jobId }),
      });
      setApplications(prev => [res, ...prev]);
    } catch (error) {
      console.error('Failed to create application:', error);
      throw error;
    }
  };

  const updateApplicationStatus = async (id: string, status: string) => {
    // Optimistic UI update
    setApplications(apps => apps.map(app => 
      app.id === id ? { ...app, status } : app
    ));

    try {
      await fetchApi(`/applications/${id}/transition`, {
        method: 'POST',
        body: JSON.stringify({ target_status: status }),
      });
    } catch (error) {
      console.error('Failed to update status:', error);
      // Revert on failure
      await fetchApplications();
      throw error;
    }
  };

  const deleteApplication = async (id: string) => {
    try {
      await fetchApi(`/applications/${id}`, { method: 'DELETE' });
      setApplications(prev => prev.filter(a => a.id !== id));
    } catch (error) {
      console.error('Failed to delete application:', error);
      throw error;
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  return (
    <ApplicationsContext.Provider value={{ applications, loading, fetchApplications, createApplication, updateApplicationStatus, deleteApplication }}>
      {children}
    </ApplicationsContext.Provider>
  );
}

export function useApplications() {
  const context = useContext(ApplicationsContext);
  if (context === undefined) {
    throw new Error('useApplications must be used within an ApplicationsProvider');
  }
  return context;
}
