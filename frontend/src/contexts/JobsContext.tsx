'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { fetchApi } from '@/lib/api';

export interface Job {
  id: string;
  title: string;
  company_name: string;
  company?: { name: string };
  location: string;
  employment_type: string;
  remote_status: string;
  experience_level?: string;
  source_url?: string;
  description?: string;
  created_at: string;
}

interface JobsContextType {
  jobs: Job[];
  loading: boolean;
  syncing: boolean;
  fetchJobs: () => Promise<void>;
  syncProviderJobs: (provider: string, what?: string, where?: string) => Promise<any>;
  addManualJob: (job: Partial<Job>) => Promise<void>;
}

const JobsContext = createContext<JobsContextType | undefined>(undefined);

export function JobsProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await fetchApi('/jobs');
      if (data && data.items) {
        setJobs(data.items);
      }
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const syncProviderJobs = async (provider: string, what?: string, where?: string) => {
    setSyncing(true);
    try {
      const result = await fetchApi('/jobs/sync', {
        method: 'POST',
        body: JSON.stringify({
          provider_name: provider,
          what: what,
          where: where,
          // SerpApi / new providers use query/location
          query: what,
          location: where,
        })
      });
      // Refresh local jobs list after a successful sync
      await fetchJobs();
      return result;
    } catch (error) {
      console.error(`Failed to sync jobs from ${provider}:`, error);
      throw error;
    } finally {
      setSyncing(false);
    }
  };

  const addManualJob = async (jobData: Partial<Job>) => {
    try {
      const res = await fetchApi('/jobs', {
        method: 'POST',
        body: JSON.stringify(jobData),
      });
      setJobs(prev => [res, ...prev]);
    } catch (error) {
      console.error('Failed to add manual job:', error);
      throw error;
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  return (
    <JobsContext.Provider value={{ jobs, loading, syncing, fetchJobs, syncProviderJobs, addManualJob }}>
      {children}
    </JobsContext.Provider>
  );
}

export function useJobs() {
  const context = useContext(JobsContext);
  if (context === undefined) {
    throw new Error('useJobs must be used within a JobsProvider');
  }
  return context;
}
