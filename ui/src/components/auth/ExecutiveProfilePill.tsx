import React, { useState, useRef, useEffect } from 'react';
import { UserProfile } from '../../api';

interface ExecutiveProfilePillProps {
  user: UserProfile;
  onLogout: () => void;
}

export const ExecutiveProfilePill: React.FC<ExecutiveProfilePillProps> = ({ user, onLogout }) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Compute initials from name or email
  const initials = user.full_name
    ? user.full_name
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((n) => n[0].toUpperCase())
        .join('')
    : user.email.slice(0, 2).toUpperCase();

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        className="flex items-center gap-2 px-2 py-0.5 rounded-md bg-[#222222] hover:bg-[#2a2a2a] border border-[#2e2e2e] text-slate-200 transition-all text-xs focus:outline-none shadow-sm cursor-pointer"
        title="Executive Account Settings"
      >
        <div className="w-5 h-5 rounded bg-gradient-to-tr from-brand-600 to-purple-400 flex items-center justify-center text-slate-950 font-bold text-[10px] shadow-sm">
          {initials}
        </div>
        <div className="text-left hidden sm:block">
          <p className="font-semibold text-white leading-tight truncate max-w-[120px] text-xs">
            {user.full_name || user.email}
          </p>
        </div>
        <svg
          className={`w-3 h-3 text-slate-400 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {dropdownOpen && (
        <div className="absolute right-0 mt-2 w-64 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl shadow-black/80 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150 backdrop-blur-xl">
          <div className="px-3.5 py-2.5 border-b border-slate-800/80">
            <p className="text-xs font-semibold text-white">{user.full_name}</p>
            <p className="text-[11px] text-slate-400 truncate">{user.email}</p>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-brand-950/90 text-brand-400 border border-brand-800/60 font-mono">
                {user.role}
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                ID: {user.id.slice(0, 10)}
              </span>
            </div>
          </div>

          <div className="py-1">
            <div className="px-3.5 py-1.5 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Security</span>
              <span className="text-emerald-400 font-medium">Session Active</span>
            </div>
            <div className="px-3.5 py-1.5 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Governance</span>
              <span className="text-slate-300">Human Sign-off</span>
            </div>
          </div>

          <div className="border-t border-slate-800/80 pt-1 mt-1">
            <button
              onClick={() => {
                setDropdownOpen(false);
                onLogout();
              }}
              className="w-full text-left px-3.5 py-2 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 flex items-center gap-2 transition"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
              <span>Sign Out of Console</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
