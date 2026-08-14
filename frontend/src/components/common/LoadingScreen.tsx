'use client';

import { useState, useEffect } from 'react';

interface LoadingScreenProps {
  title?: string;
  subtitle?: string;
  fullScreen?: boolean;
}

const PHRASES = [
  'Preparing your career workspace...',
  'Connecting AI intelligence pipeline...',
  'Synchronizing applications & contacts...',
  'Calibrating personalized insights...',
];

export function LoadingScreen({
  title = 'Ascendra',
  subtitle,
  fullScreen = true,
}: LoadingScreenProps) {
  const [phraseIndex, setPhraseIndex] = useState(0);

  useEffect(() => {
    if (subtitle) return;
    const interval = setInterval(() => {
      setPhraseIndex((prev) => (prev + 1) % PHRASES.length);
    }, 2400);
    return () => clearInterval(interval);
  }, [subtitle]);

  return (
    <div
      className={`${
        fullScreen ? 'fixed inset-0 z-50 min-h-screen' : 'w-full py-16'
      } bg-gradient-to-br from-[#F4FBF7] via-[#E6F4ED] to-[#F0FDFA] flex flex-col items-center justify-center p-6 relative overflow-hidden select-none`}
    >
      {/* Ambient background glowing orbs */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[30rem] h-[30rem] bg-emerald-400/20 rounded-full blur-3xl pointer-events-none animate-pulse-glow" />
      <div
        className="absolute bottom-1/4 left-1/3 w-[24rem] h-[24rem] bg-teal-400/20 rounded-full blur-3xl pointer-events-none animate-pulse-glow"
        style={{ animationDelay: '1.5s' }}
      />

      {/* Main Glassmorphic Loading Card */}
      <div className="relative z-10 glass-panel px-9 py-11 max-w-sm w-full flex flex-col items-center text-center shadow-[0_25px_70px_-15px_rgba(5,150,105,0.18)] border border-emerald-200/80">
        
        {/* Curved Fluid Multi-Orbital Animation */}
        <div className="relative w-28 h-28 mb-7 flex items-center justify-center">
          
          {/* 1. Ambient Glow Halo */}
          <div className="absolute inset-2 rounded-full bg-gradient-to-tr from-emerald-500/30 via-teal-400/25 to-emerald-400/20 blur-xl animate-pulse-glow" />

          {/* 2. Outer Curly / Sweeping Circular Gradient Arc (Smooth Curved Ribbon) */}
          <svg
            className="absolute inset-0 w-full h-full animate-orbit-spin"
            viewBox="0 0 100 100"
            fill="none"
          >
            <defs>
              <linearGradient id="outerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#059669" stopOpacity="1" />
                <stop offset="60%" stopColor="#10B981" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#0D9488" stopOpacity="0" />
              </linearGradient>
            </defs>
            {/* Background subtle full curved track */}
            <circle
              cx="50"
              cy="50"
              r="44"
              stroke="#A7F3D0"
              strokeWidth="2.5"
              strokeOpacity="0.35"
            />
            {/* Outer fluid sweeping curly arc */}
            <circle
              cx="50"
              cy="50"
              r="44"
              stroke="url(#outerGrad)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="140 280"
              className="animate-dash-flow"
            />
          </svg>

          {/* 3. Middle Counter-Rotating Curved Teal Arc */}
          <svg
            className="absolute inset-2 w-[calc(100%-1rem)] h-[calc(100%-1rem)] animate-orbit-spin-reverse"
            viewBox="0 0 100 100"
            fill="none"
          >
            <defs>
              <linearGradient id="innerGrad" x1="100%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#0D9488" stopOpacity="0.95" />
                <stop offset="70%" stopColor="#34D399" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#14B8A6" stopOpacity="0" />
              </linearGradient>
            </defs>
            <circle
              cx="50"
              cy="50"
              r="42"
              stroke="url(#innerGrad)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeDasharray="85 180"
            />
          </svg>

          {/* 4. Orbiting Glowing Satellite Bead */}
          <div className="absolute inset-0 animate-orbit-spin">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_#34D399] -translate-y-1 mx-auto" />
          </div>

          {/* 5. Center Brand Badge with Breathing Glow and Float */}
          <div className="relative z-10 w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 via-emerald-600 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-600/35 animate-breathe">
            <svg
              className="w-7 h-7 text-white drop-shadow"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z"
              />
            </svg>
          </div>

        </div>

        {/* Brand Name & Title */}
        <h1 className="text-2xl font-black tracking-tight bg-gradient-to-r from-emerald-900 via-emerald-700 to-teal-800 bg-clip-text text-transparent mb-1">
          {title}
        </h1>

        {/* Dynamic / Prop Subtitle */}
        <div className="h-6 flex items-center justify-center mb-6">
          <p className="text-xs font-semibold text-emerald-800/75 tracking-wide transition-all duration-300 animate-in fade-in">
            {subtitle || PHRASES[phraseIndex]}
          </p>
        </div>

        {/* Modern Shimmer Progress Rail */}
        <div className="w-full h-1.5 bg-emerald-100/90 rounded-full overflow-hidden relative shadow-inner mb-4">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-500 rounded-full w-full animate-shimmer-bar" />
        </div>

        {/* Synchronized Bouncing Indicator Dots */}
        <div className="flex items-center justify-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/90 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-teal-500/90 animate-bounce" style={{ animationDelay: '160ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600/90 animate-bounce" style={{ animationDelay: '320ms' }} />
        </div>

      </div>
    </div>
  );
}
