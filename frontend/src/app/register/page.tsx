'use client';

import { useState } from 'react';
import { supabase } from '@/lib/supabase';
import Link from 'next/link';
import { Loader2, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function Register() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const router = useRouter();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          }
        }
      });

      if (error) throw error;

      if (data?.session) {
        // Email confirmation disabled — user is authenticated immediately
        router.push('/dashboard');
      } else if (data?.user && !data?.session) {
        // Email confirmation enabled — tell user to check email
        setSuccess('Registration successful! Please check your email to verify your account, then come back and sign in.');
      } else {
        setSuccess('Registration successful! You can now sign in.');
      }
    } catch (err: any) {
      const msg = err.message || '';
      const status = err.status || 0;
      if (status === 500 || msg.includes('500') || msg.includes('Internal Server Error') || msg.includes('Username and Password not accepted') || msg.includes('SMTP') || msg.includes('BadCredentials')) {
        setError('Registration is temporarily experiencing issues with email delivery. Please try again in a few moments, or contact support if the problem persists.');
      } else if (status === 429 || msg.includes('rate limit') || msg.includes('too many')) {
        setError('Too many signup attempts. Please wait a moment and try again.');
      } else if (msg.includes('already registered') || msg.includes('already exists') || msg.includes('already been registered')) {
        setError('An account with this email already exists. Try logging in instead.');
      } else {
        setError(msg || 'Failed to register. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent flex flex-col justify-center py-12 sm:px-6 lg:px-8 selection:bg-emerald-500/20 relative z-10">
      <div className="absolute top-1/4 right-1/4 w-[500px] h-[500px] bg-gradient-to-br from-emerald-500/20 to-teal-500/10 rounded-full blur-3xl -z-10" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="relative flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 shadow-md shadow-emerald-500/30">
            <Sparkles className="w-6 h-6 text-white animate-pulse" />
          </div>
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-emerald-950">
          Create your account
        </h2>
        <p className="mt-1 text-center text-sm text-emerald-800/70 font-medium">Join Ascendra AI Reverse Headhunting</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="glass-panel py-8 px-6 shadow-xl sm:px-10">

          {error && (
            <div className="bg-rose-50 border border-rose-200 text-rose-600 p-3 rounded-xl text-xs font-semibold mb-6">
              {error}
            </div>
          )}

          {/* Social Sign Up */}
          <button
            type="button"
            onClick={async () => {
              try {
                setLoading(true);
                const { error } = await supabase.auth.signInWithOAuth({
                  provider: 'google',
                  options: {
                    redirectTo: `${window.location.origin}/dashboard`,
                  },
                });
                if (error) throw error;
              } catch (err: any) {
                setError(err.message || 'Google sign-up failed');
                setLoading(false);
              }
            }}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 py-2.5 px-4 border border-emerald-200/80 rounded-xl bg-white hover:bg-emerald-50/50 text-sm font-semibold text-emerald-900 transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed mb-6"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Sign up with Google
          </button>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-emerald-100" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-3 bg-white text-emerald-800/50 font-medium">or register with email</span>
            </div>
          </div>

          {success ? (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 p-4 rounded-xl text-xs font-bold mb-6 text-center space-y-2">
              <p>✅ {success}</p>
              <Link href="/login" className="inline-block mt-2 text-xs font-extrabold text-emerald-800 underline">
                Go to Sign In &rarr;
              </Link>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleRegister}>
              <div>
                <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Harsh Verma"
                  className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-emerald-900 uppercase tracking-wider mb-1">Password</label>
                <input
                  type="password"
                  required
                  pattern="(?=.*[A-Z])(?=.*[!@#$&*]).{8,}"
                  title="Must be at least 8 characters, contain 1 uppercase letter and 1 special character (!@#$&*)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-50 border border-emerald-200/80 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-sm"
                />
                <p className="mt-1 text-[11px] text-emerald-800/60 font-medium">
                  At least 8 characters with 1 uppercase & 1 special symbol.
                </p>
              </div>

              {/* Informational Callout */}
              <div className="bg-emerald-50/80 border border-emerald-200 p-3 rounded-xl text-[11px] text-emerald-950 font-medium leading-tight">
                💡 <strong>100% Free Tier Included:</strong> SerpApi Google Jobs searching, unlimited free job board aggregation, and AI resume tailoring are enabled automatically upon signup.
              </div>

              <button disabled={loading} type="submit" className="w-full btn-primary py-3 text-sm flex justify-center items-center mt-2">
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Create Account'}
              </button>
            </form>
          )}

          <div className="mt-6 text-center text-xs font-medium">
            <span className="text-emerald-900/70">Already have an account? </span>
            <Link href="/login" className="font-bold text-emerald-700 hover:text-emerald-900 transition-colors">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
