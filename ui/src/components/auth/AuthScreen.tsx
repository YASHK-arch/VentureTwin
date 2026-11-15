import React, { useState, useEffect, useRef } from 'react';
import { login, register, forgotPassword, UserProfile } from '../../api';
import { VentureTwinLogo } from './VentureTwinLogo';

interface AuthScreenProps {
  onAuthenticated: (user: UserProfile) => void;
  initialMode?: 'login' | 'register';
  skipIntro?: boolean;
}

type AnimationPhase =
  | 'intro_logo'      // 0ms - 700ms: Center scale-up + glow
  | 'intro_interact'  // 700ms - 1300ms: Light sweep & 3D pulse
  | 'auth_form'       // Form visible and ready for interaction
  | 'login_confirm'   // Success badge & emerald pulse
  | 'flying_to_nav';  // Logo flies to top-left header position

export const AuthScreen: React.FC<AuthScreenProps> = ({
  onAuthenticated,
  initialMode = 'login',
  skipIntro = false
}) => {
  const [viewMode, setViewMode] = useState<'login' | 'register' | 'forgot'>(initialMode);
  const [phase, setPhase] = useState<AnimationPhase>(skipIntro ? 'auth_form' : 'intro_logo');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [rememberMe, setRememberMe] = useState(true);

  // Status & feedback
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // Reference for flying transition coordinates
  const logoWrapperRef = useRef<HTMLDivElement>(null);

  // Check for reduced motion preference
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mediaQuery.matches && phase !== 'auth_form') {
      setPhase('auth_form');
    }
  }, [phase]);

  // Entrance animation timer sequence
  useEffect(() => {
    if (skipIntro) {
      setPhase('auth_form');
      return;
    }

    const t1 = setTimeout(() => {
      setPhase((prev) => (prev === 'intro_logo' ? 'intro_interact' : prev));
    }, 700);

    const t2 = setTimeout(() => {
      setPhase((prev) => (prev === 'intro_interact' ? 'auth_form' : prev));
    }, 1400);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [skipIntro]);

  const handleSkipIntro = () => {
    setPhase('auth_form');
  };

  const handleQuickFillCEO = () => {
    setEmail('ceo@nimbusdesk.io');
    setPassword('VentureTwin2026!');
    setErrorMsg(null);
  };

  const executeSuccessfulLoginTransition = (user: UserProfile) => {
    setPhase('login_confirm');
    setTimeout(() => {
      setPhase('flying_to_nav');
      setTimeout(() => {
        onAuthenticated(user);
      }, 650);
    }, 450);
  };

  const handleSubmitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMsg('Please enter both your email and password.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await login({ email: email.trim(), password, remember_me: rememberMe });
      executeSuccessfulLoginTransition(res.user);
    } catch (err: any) {
      setErrorMsg(err.message || 'Invalid executive credentials. Please verify your login details.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim() || !password) {
      setErrorMsg('All fields are required to register.');
      return;
    }
    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters in length.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMsg('Password confirmation does not match.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await register({
        full_name: fullName.trim(),
        email: email.trim(),
        password
      });
      executeSuccessfulLoginTransition(res.user);
    } catch (err: any) {
      setErrorMsg(err.message || 'Registration failed. An account with this email may already exist.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setErrorMsg('Please enter your account email.');
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await forgotPassword(email.trim());
      setSuccessNotice(res.message);
    } catch (err: any) {
      setErrorMsg(err.message || 'Unable to submit recovery request.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full bg-slate-950 text-slate-100 flex items-center justify-center overflow-hidden select-none font-sans">
      {/* Background Ambience & Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black pointer-events-none" />
      <div
        className="absolute inset-0 opacity-[0.03] bg-[linear-gradient(to_right,#808080_1px,transparent_1px),linear-gradient(to_bottom,#808080_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none"
      />
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Skip Intro Pill (During Initial Entry) */}
      {(phase === 'intro_logo' || phase === 'intro_interact') && (
        <button
          onClick={handleSkipIntro}
          className="absolute top-6 right-6 px-3.5 py-1.5 rounded-full bg-slate-900/80 hover:bg-slate-800 text-slate-400 hover:text-white text-xs border border-slate-800 backdrop-blur-md transition-all shadow-sm z-50 flex items-center gap-1.5"
        >
          <span>Skip Intro</span>
          <span className="text-[10px] text-slate-500">ESC</span>
        </button>
      )}

      {/* Main Orchestrating Stage Container */}
      <div className="relative z-10 w-full max-w-md px-4 sm:px-0 flex flex-col items-center">
        {/* Cinematic Animated Logo Container */}
        <div
          ref={logoWrapperRef}
          className={`transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col items-center transform-gpu ${
            phase === 'intro_logo'
              ? 'scale-100 opacity-100 translate-y-0 my-0'
              : phase === 'intro_interact'
              ? 'scale-105 opacity-100 translate-y-0 my-0'
              : phase === 'auth_form'
              ? 'scale-90 opacity-100 mb-6 translate-y-0'
              : phase === 'login_confirm'
              ? 'scale-95 opacity-100 mb-6'
              : 'scale-[0.57] -translate-x-[calc(50vw-120px)] -translate-y-[calc(50vh-32px)] opacity-90'
          }`}
        >
          <VentureTwinLogo
            size={phase === 'intro_logo' || phase === 'intro_interact' ? 'hero' : 'auth'}
            showText={true}
            showSubtitle={phase === 'intro_logo' || phase === 'intro_interact'}
            glow={true}
            pulsing={phase === 'intro_interact' || phase === 'login_confirm'}
            lightSweep={phase === 'intro_interact'}
            interactive={phase === 'auth_form'}
            className="flex-col text-center"
          />

          {/* Subtitle during Phase 1 & 2 */}
          {(phase === 'intro_logo' || phase === 'intro_interact') && (
            <div className="mt-4 flex items-center gap-2 text-xs text-brand-400 font-mono tracking-widest uppercase animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400" />
              <span>Autonomous Decision Engine</span>
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400" />
            </div>
          )}
        </div>

        {/* Authentication Card (Revealed during auth_form and login_confirm) */}
        {(phase === 'auth_form' || phase === 'login_confirm') && (
          <div
            className={`w-full rounded-2xl bg-slate-900/85 backdrop-blur-2xl border border-slate-800/90 shadow-2xl shadow-brand-950/40 p-6 sm:p-8 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] transform-gpu ${
              phase === 'login_confirm' ? 'opacity-90 scale-[0.99]' : 'opacity-100 translate-y-0 scale-100'
            }`}
          >
            {/* Header / Tabs */}
            <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-800/80">
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight">
                  {viewMode === 'login'
                    ? 'Executive Sign In'
                    : viewMode === 'register'
                    ? 'Create Executive Account'
                    : 'Account Recovery'}
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  {viewMode === 'login'
                    ? 'Authenticate to access the operational flight console'
                    : viewMode === 'register'
                    ? 'Initialize credentials for multi-agent simulation'
                    : 'Dispatch recovery link to registered executive email'}
                </p>
              </div>

              {/* Mode Toggle Pills */}
              {viewMode !== 'forgot' && (
                <div className="flex items-center p-1 bg-slate-950 rounded-lg border border-slate-800/80 text-xs">
                  <button
                    type="button"
                    onClick={() => {
                      setViewMode('login');
                      setErrorMsg(null);
                    }}
                    className={`px-2.5 py-1 rounded-md font-medium transition ${
                      viewMode === 'login'
                        ? 'bg-brand-500 text-slate-950 font-bold shadow'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setViewMode('register');
                      setErrorMsg(null);
                    }}
                    className={`px-2.5 py-1 rounded-md font-medium transition ${
                      viewMode === 'register'
                        ? 'bg-brand-500 text-slate-950 font-bold shadow'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Register
                  </button>
                </div>
              )}
            </div>

            {/* Error Notification Banner */}
            {errorMsg && (
              <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start justify-between gap-2 animate-in fade-in duration-200">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-rose-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{errorMsg}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setErrorMsg(null)}
                  className="text-rose-400 hover:text-rose-200 text-sm font-bold leading-none"
                >
                  &times;
                </button>
              </div>
            )}

            {/* Success Notification Banner */}
            {successNotice && (
              <div className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-start gap-2 animate-in fade-in duration-200">
                <svg className="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>{successNotice}</span>
              </div>
            )}

            {/* LOGIN FORM */}
            {viewMode === 'login' && (
              <form onSubmit={handleSubmitLogin} className="space-y-4">
                {/* One-Click Evaluator Seed Pill */}
                <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-slate-300 font-medium">Demo Executive:</span>
                    <span className="text-brand-400 font-mono text-[11px]">ceo@nimbusdesk.io</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleQuickFillCEO}
                    className="px-2 py-0.5 rounded bg-brand-500/20 hover:bg-brand-500/30 text-brand-300 hover:text-white border border-brand-500/30 font-semibold text-[10px] transition"
                  >
                    Auto-Fill
                  </button>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5" htmlFor="login-email">
                    Executive Email
                  </label>
                  <div className="relative">
                    <input
                      id="login-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="ceo@nimbusdesk.io"
                      required
                      autoFocus
                      disabled={loading || phase === 'login_confirm'}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-white text-xs placeholder-slate-600 outline-none transition disabled:opacity-50"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-semibold text-slate-300" htmlFor="login-password">
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setViewMode('forgot');
                        setErrorMsg(null);
                        setSuccessNotice(null);
                      }}
                      className="text-[11px] text-brand-400 hover:text-brand-300 transition"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <input
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      required
                      disabled={loading || phase === 'login_confirm'}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-white text-xs placeholder-slate-600 outline-none transition pr-10 disabled:opacity-50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 focus:outline-none"
                    >
                      {showPassword ? (
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3l18 18M10.5 10.677a2 2 0 002.823 2.823M7.362 7.561C5.68 8.74 4.279 10.42 3.5 12c1.8 3.6 5.5 6 9.5 6 1.4 0 2.7-.3 3.9-.9m2.5-1.9c1.4-1 2.5-2.2 3.1-3.2-1.8-3.6-5.5-6-9.5-6-.8 0-1.6.1-2.4.3" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center">
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="rounded bg-slate-950 border-slate-800 text-brand-500 focus:ring-0 focus:ring-offset-0"
                    />
                    <span>Remember session for 30 days</span>
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={loading || phase === 'login_confirm'}
                  className={`w-full py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-2 shadow-lg transition-all duration-300 ${
                    phase === 'login_confirm'
                      ? 'bg-emerald-500 text-slate-950 shadow-emerald-500/30'
                      : 'bg-brand-500 hover:bg-brand-400 text-slate-950 shadow-brand-500/25 hover:shadow-brand-500/40'
                  } disabled:opacity-60 disabled:cursor-not-allowed`}
                >
                  {phase === 'login_confirm' ? (
                    <>
                      <svg className="w-4 h-4 text-slate-950 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Executive Session Verified</span>
                    </>
                  ) : loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                      <span>Authenticating...</span>
                    </>
                  ) : (
                    <>
                      <span>Enter Decision Console</span>
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                      </svg>
                    </>
                  )}
                </button>
              </form>
            )}

            {/* REGISTER FORM */}
            {viewMode === 'register' && (
              <form onSubmit={handleSubmitRegister} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1" htmlFor="reg-name">
                    Full Name & Title
                  </label>
                  <input
                    id="reg-name"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Elena Rostova (CEO)"
                    required
                    disabled={loading || phase === 'login_confirm'}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-white text-xs placeholder-slate-600 outline-none transition disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1" htmlFor="reg-email">
                    Corporate Email
                  </label>
                  <input
                    id="reg-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="executive@company.io"
                    required
                    disabled={loading || phase === 'login_confirm'}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-white text-xs placeholder-slate-600 outline-none transition disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1" htmlFor="reg-password">
                    Password (min. 8 characters)
                  </label>
                  <div className="relative">
                    <input
                      id="reg-password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      required
                      disabled={loading || phase === 'login_confirm'}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-white text-xs placeholder-slate-600 outline-none transition pr-10 disabled:opacity-50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      {showPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1" htmlFor="reg-confirm">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <input
                      id="reg-confirm"
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••••••"
                      required
                      disabled={loading || phase === 'login_confirm'}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-white text-xs placeholder-slate-600 outline-none transition pr-10 disabled:opacity-50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      {showConfirmPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading || phase === 'login_confirm'}
                  className="w-full py-2.5 rounded-xl bg-brand-500 hover:bg-brand-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-brand-500/25 transition disabled:opacity-60"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                      <span>Creating Profile...</span>
                    </>
                  ) : (
                    <span>Register & Launch Session</span>
                  )}
                </button>
              </form>
            )}

            {/* FORGOT PASSWORD FORM */}
            {viewMode === 'forgot' && (
              <form onSubmit={handleSubmitForgotPassword} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5" htmlFor="forgot-email">
                    Account Email Address
                  </label>
                  <input
                    id="forgot-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="ceo@nimbusdesk.io"
                    required
                    disabled={loading}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-white text-xs placeholder-slate-600 outline-none transition disabled:opacity-50"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 rounded-xl bg-brand-500 hover:bg-brand-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-brand-500/25 transition disabled:opacity-60"
                >
                  {loading ? 'Processing...' : 'Send Recovery Instructions'}
                </button>

                <div className="text-center pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setViewMode('login');
                      setErrorMsg(null);
                      setSuccessNotice(null);
                    }}
                    className="text-xs text-brand-400 hover:text-brand-300 font-medium transition"
                  >
                    &larr; Back to Sign In
                  </button>
                </div>
              </form>
            )}

            {/* Security Guarantee Footer */}
            <div className="mt-5 pt-4 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
              <span className="flex items-center gap-1">
                <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                PBKDF2-SHA256 Encrypted
              </span>
              <span>Human-in-the-Loop Sign-Off</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
