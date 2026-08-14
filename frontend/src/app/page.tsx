import Link from 'next/link';
import { ArrowRight, Search, FileText, BarChart3, Sparkles, Wand2, ShieldCheck, Zap } from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen bg-transparent flex flex-col selection:bg-emerald-500/20">
      {/* Navigation */}
      <nav className="w-full px-6 py-4 flex justify-between items-center max-w-7xl mx-auto mt-4 glass-panel relative z-20">
        <div className="flex items-center space-x-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 shadow-md shadow-emerald-500/30">
            <Sparkles className="w-5 h-5 text-white animate-pulse" />
          </div>
          <span className="font-extrabold text-xl bg-clip-text text-transparent bg-gradient-to-r from-emerald-800 via-teal-600 to-emerald-900 tracking-tight">
            Ascendra
          </span>
        </div>
        <div className="flex items-center space-x-4">
          <Link href="/login" className="text-emerald-900 hover:text-emerald-700 font-semibold text-sm transition-colors">
            Login
          </Link>
          <Link href="/register">
            <button className="btn-primary flex items-center text-sm group">
              Get Started
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
            </button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-20 text-center relative z-10">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-br from-emerald-500/20 via-teal-500/15 to-emerald-400/10 rounded-full blur-3xl -z-10" />
        
        <div className="inline-flex items-center space-x-2 bg-emerald-50/80 backdrop-blur border border-emerald-200/60 rounded-full px-4 py-1.5 mb-8 shadow-sm">
          <Sparkles className="h-3.5 w-3.5 text-emerald-600 animate-spin" style={{ animationDuration: '6s' }} />
          <span className="text-xs font-bold text-emerald-900 tracking-wide">Next-Gen Reverse Headhunting Engine</span>
        </div>
        
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-emerald-950 max-w-4xl leading-[1.1] mb-6">
          Reverse Headhunting, <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-500">
            Powered by Autonomous AI.
          </span>
        </h1>
        
        <p className="text-lg md:text-xl text-emerald-900/80 max-w-2xl mx-auto mb-10 leading-relaxed font-medium">
          Track target roles, tailor PDF resumes in 1-click, and generate hyper-personalized outreach emails directly for recruiters.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-center w-full max-w-md mx-auto">
          <Link href="/register" className="w-full">
            <button className="btn-primary w-full py-4 text-base flex items-center justify-center group shadow-xl shadow-emerald-500/25">
              Launch Career Engine
              <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
            </button>
          </Link>
        </div>

        {/* Feature grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto mt-24">
          <div className="glass-card p-8 text-left">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-6 text-emerald-600 shadow-sm">
              <Search className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-emerald-950 mb-2">Target Job Tracker</h3>
            <p className="text-emerald-900/70 text-sm font-medium leading-relaxed">Save target job opportunities and manage your pipeline through an intuitive Kanban board.</p>
          </div>
          
          <div className="glass-card p-8 text-left">
            <div className="w-12 h-12 rounded-2xl bg-teal-50 border border-teal-100 flex items-center justify-center mb-6 text-teal-600 shadow-sm">
              <Wand2 className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-emerald-950 mb-2">1-Click Resume Tailoring</h3>
            <p className="text-emerald-900/70 text-sm font-medium leading-relaxed">AI analyzes job requirements and optimizes your base resume without fabricating facts.</p>
          </div>
          
          <div className="glass-card p-8 text-left">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-6 text-emerald-600 shadow-sm">
              <Zap className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-emerald-950 mb-2">Outreach Assistant</h3>
            <p className="text-emerald-900/70 text-sm font-medium leading-relaxed">Generate cold emails tuned for recruiter response rates and manage contact connections.</p>
          </div>
        </div>
      </div>
    </main>
  );
}
