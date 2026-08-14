import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { JobsProvider } from '@/contexts/JobsContext';
import { ApplicationsProvider } from '@/contexts/ApplicationsContext';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30">
        <Sidebar />
        <div className="ml-64 flex flex-col min-h-screen">
          <Header />
          <main className="flex-1 p-8 overflow-x-hidden">
            <div className="max-w-7xl mx-auto">
              <JobsProvider>
                <ApplicationsProvider>
                  {children}
                </ApplicationsProvider>
              </JobsProvider>
            </div>
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
