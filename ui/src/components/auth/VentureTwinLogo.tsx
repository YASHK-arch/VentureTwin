import React from 'react';

export interface VentureTwinLogoProps {
  size?: 'hero' | 'auth' | 'nav' | 'inline';
  showText?: boolean;
  showSubtitle?: boolean;
  glow?: boolean;
  pulsing?: boolean;
  interactive?: boolean;
  lightSweep?: boolean;
  className?: string;
  badgeText?: string;
}

export const VentureTwinLogo: React.FC<VentureTwinLogoProps> = ({
  size = 'auth',
  showText = true,
  showSubtitle = false,
  glow = true,
  pulsing = false,
  interactive = false,
  lightSweep = false,
  className = '',
  badgeText = 'SwarmFlow Engine'
}) => {
  const sizeConfig = {
    hero: {
      box: 'w-24 h-24 rounded-2xl',
      font: 'text-3xl font-extrabold',
      title: 'text-3xl font-bold tracking-tight',
      sub: 'text-sm text-slate-400 max-w-sm',
      ring: 'inset-[-12px]',
      glowBlur: 'blur-2xl',
    },
    auth: {
      box: 'w-14 h-14 rounded-xl',
      font: 'text-xl font-bold',
      title: 'text-xl font-bold tracking-tight',
      sub: 'text-xs text-slate-400',
      ring: 'inset-[-8px]',
      glowBlur: 'blur-xl',
    },
    nav: {
      box: 'w-8 h-8 rounded-lg',
      font: 'text-sm font-bold',
      title: 'text-sm font-bold tracking-tight',
      sub: 'text-[10px] text-slate-400',
      ring: 'inset-[-4px]',
      glowBlur: 'blur-md',
    },
    inline: {
      box: 'w-6 h-6 rounded-md',
      font: 'text-xs font-bold',
      title: 'text-xs font-semibold tracking-tight',
      sub: 'text-[9px] text-slate-400',
      ring: 'inset-[-2px]',
      glowBlur: 'blur-sm',
    }
  }[size];

  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* 3D Glass Badge Container */}
      <div className="relative group flex items-center justify-center">
        {/* Ambient Radial Glow */}
        {glow && (
          <div
            className={`absolute -inset-2 bg-gradient-to-r from-brand-500/40 via-emerald-500/30 to-teal-400/40 rounded-3xl ${sizeConfig.glowBlur} opacity-70 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none ${
              pulsing ? 'animate-pulse' : ''
            }`}
          />
        )}

        {/* Outer Orbital Ring */}
        {size === 'hero' && (
          <div className="absolute inset-[-14px] rounded-full border border-brand-500/30 animate-[spin_12s_linear_infinite] pointer-events-none">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-brand-400 shadow-[0_0_8px_#14b8a6]" />
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]" />
          </div>
        )}

        {/* 3D Prism Tile */}
        <div
          className={`relative ${sizeConfig.box} bg-gradient-to-br from-brand-400 via-brand-500 to-emerald-600 flex items-center justify-center text-slate-950 font-mono shadow-xl shadow-brand-500/25 border border-teal-200/40 overflow-hidden transform-gpu transition-all duration-500 ${
            interactive ? 'hover:scale-105 hover:rotate-1' : ''
          }`}
          style={{
            boxShadow: '0 8px 32px -4px rgba(20, 184, 166, 0.35), inset 0 1px 1px rgba(255, 255, 255, 0.4)'
          }}
        >
          {/* Subtle Diagonal Glass Texture */}
          <div className="absolute inset-0 bg-gradient-to-tr from-black/20 via-transparent to-white/30 pointer-events-none" />

          {/* Light Sweep Shimmer Effect */}
          {lightSweep && (
            <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/40 to-transparent animate-[shimmer_2.5s_infinite] pointer-events-none" />
          )}

          {/* Inner Sharp Monogram */}
          <span className={`relative z-10 ${sizeConfig.font} tracking-tighter text-slate-950 drop-shadow-sm`}>
            VT
          </span>
        </div>
      </div>

      {/* Brand Wordmark & Metadata */}
      {showText && (
        <div className="flex flex-col text-left">
          <div className="flex items-center gap-2">
            <span className={`${sizeConfig.title} text-white font-extrabold tracking-tight`}>
              VentureTwin
            </span>
            {badgeText && size !== 'nav' && size !== 'inline' && (
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase bg-brand-950/80 text-brand-400 border border-brand-800/80 shadow-sm">
                {badgeText}
              </span>
            )}
            {size === 'nav' && badgeText && (
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase bg-slate-800 text-slate-300">
                {badgeText}
              </span>
            )}
          </div>
          {showSubtitle && (
            <p className={`${sizeConfig.sub} leading-relaxed mt-0.5`}>
              AI Flight Simulator & Operational Digital Twin for SaaS CEOs
            </p>
          )}
        </div>
      )}
    </div>
  );
};
