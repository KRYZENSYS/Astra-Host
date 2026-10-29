import React, { useState } from 'react';
import { User } from '../types';
import { botStore } from '../lib/store';
import { uz } from '../locales/uz';
import {
  X,
  Lock,
  Mail,
  UserCheck,
  ShieldCheck,
  ArrowRight,
  AlertCircle,
} from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: User;
  onSuccess: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onSuccess,
}) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('afirdavs135@gmail.com');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password.trim()) {
      setError("Elektron pochta va maxfiy parolni kiriting.");
      return;
    }

    const res = botStore.login(email, password);
    if (!res.success) {
      setError(res.error || "Parol yoki elektron pochta noto'g'ri.");
      return;
    }

    onSuccess();
    onClose();
  };

  const handleQuickSwitch = (asAdmin: boolean) => {
    botStore.switchDemoAccount(asAdmin);
    onSuccess();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#111726] border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0d121f]">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Lock className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-semibold text-slate-100">
              {mode === 'login' ? uz.signIn : uz.signUp}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-4">
          {/* Quick Demo Switcher Buttons for Review */}
          <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Tezkor sinov (Demo hisoblar):
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleQuickSwitch(false)}
                className="flex items-center justify-center gap-1.5 py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/60 rounded-lg text-xs font-medium transition-colors"
              >
                <UserCheck className="w-3.5 h-3.5 text-cyan-400" />
                <span>Oddiy (Free)</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickSwitch(true)}
                className="flex items-center justify-center gap-1.5 py-1.5 px-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-lg text-xs font-medium transition-colors"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Admin (Paid)</span>
              </button>
            </div>
          </div>

          {error && (
            <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Elektron pochta manzili
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="nom@mail.uz"
                  className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Parol (Argon2 bilan himoyalangan)
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 px-4 bg-emerald-400 hover:bg-emerald-300 text-slate-950 font-semibold rounded-lg text-xs flex items-center justify-center gap-2 shadow-sm transition-all active:scale-95"
            >
              <span>{mode === 'login' ? uz.signIn : uz.signUp}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="pt-2 text-center text-xs text-slate-400">
            {mode === 'login' ? (
              <button
                onClick={() => setMode('register')}
                className="text-emerald-400 hover:underline"
              >
                Hisobingiz yo'qmi? Ro'yxatdan o'tish
              </button>
            ) : (
              <button
                onClick={() => setMode('login')}
                className="text-emerald-400 hover:underline"
              >
                Profilingiz bormi? Tizimga kirish
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
