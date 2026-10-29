import React from 'react';
import { uz } from '../locales/uz';
import { User } from '../types';
import { getPlanLimits } from '../lib/botLogic';
import { Server, UserCheck, Plus, ShieldCheck, LogIn, LogOut, Sparkles, Lock } from 'lucide-react';

interface NavbarProps {
  currentUser: User | null;
  onOpenCreateBot: () => void;
  onOpenAnalyzer?: () => void;
  onOpenAuth: () => void;
  onLogout: () => void;
  onLockSite?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  onOpenCreateBot,
  onOpenAnalyzer,
  onOpenAuth,
  onLogout,
  onLockSite,
}) => {
  const limits = getPlanLimits(currentUser?.plan || 'free');

  return (
    <header className="sticky top-0 z-40 bg-[#0d121f]/95 backdrop-blur-md border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Zone 1: Brand Wordmark */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white">
              {uz.brandName}
            </span>
            <span className="hidden sm:inline text-xs text-slate-400 ml-2">
              Docker 24/7 Hosting (Shaxsiy)
            </span>
          </div>
        </div>

        {/* Zone 2: Hardening Banner */}
        <div className="hidden lg:flex items-center gap-2 text-xs text-slate-400">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Izolyatsiya: non-root UID 10001 · read-only rootfs · {limits.ramMb}MB RAM</span>
        </div>

        {/* Zone 3: Primary Actions & User Auth */}
        <div className="flex items-center gap-2.5 shrink-0">
          {currentUser ? (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  const newPlan = currentUser.plan === 'free' ? 'paid' : 'free';
                  import('../lib/store').then(({ botStore }) => {
                    botStore.switchPlan(newPlan);
                  });
                }}
                title="Tarifni almashtirish (Bepul <-> Pro)"
                className="hidden md:flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-slate-900 border border-slate-700/80 text-amber-300 hover:border-amber-400/50 transition-colors"
              >
                <span>Tarif: {currentUser.plan === 'paid' ? 'PRO (5 bot)' : 'BEPUL (1 bot)'}</span>
              </button>

              <button
                type="button"
                onClick={onOpenAuth}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-300 bg-slate-900 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors"
              >
                <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span className="font-mono text-[11px] truncate max-w-[130px]">{currentUser.email}</span>
              </button>

              {onLockSite && (
                <button
                  type="button"
                  onClick={onLockSite}
                  title="Saytni parol bilan qulflash"
                  className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg transition-colors"
                >
                  <Lock className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Qulflash</span>
                </button>
              )}

              <button
                type="button"
                onClick={onLogout}
                title="Tizimdan chiqish"
                className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800/60 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={onOpenAuth}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-200 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700/60 rounded-lg transition-colors"
            >
              <LogIn className="w-3.5 h-3.5 text-emerald-400" />
              <span>Kirish</span>
            </button>
          )}

          <button
            onClick={onOpenAnalyzer || onOpenCreateBot}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-indigo-600 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 rounded-lg shadow-sm shadow-indigo-500/20 transition-all whitespace-nowrap shrink-0 active:scale-95"
          >
            <Sparkles className="w-4 h-4 text-emerald-300" />
            <span>Aqlli Tahlilchi</span>
          </button>

          <button
            onClick={onOpenCreateBot}
            className="hidden sm:flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white border border-slate-700/60 rounded-lg shadow-sm transition-all whitespace-nowrap shrink-0 active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Oddiy yuklash</span>
          </button>
        </div>
      </div>
    </header>
  );
};
