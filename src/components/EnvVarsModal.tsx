import React, { useState } from 'react';
import { Bot } from '../types';
import { uz } from '../locales/uz';
import {
  X,
  KeyRound,
  ShieldCheck,
  Eye,
  EyeOff,
  Copy,
  Check,
  Plus,
  Trash2,
  Lock,
} from 'lucide-react';

interface EnvVarsModalProps {
  isOpen: boolean;
  onClose: () => void;
  bot: Bot;
  onSaveEnvVars: (botId: string, envVars: { key: string; value: string }[]) => void;
}

export const EnvVarsModal: React.FC<EnvVarsModalProps> = ({
  isOpen,
  onClose,
  bot,
  onSaveEnvVars,
}) => {
  const [vars, setVars] = useState<{ id?: string; key: string; value: string }[]>(
    bot.envVars.map((ev) => ({ id: ev.id, key: ev.key, value: ev.value }))
  );
  const [revealedIdx, setRevealedIdx] = useState<Record<number, boolean>>({});
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  if (!isOpen) return null;

  const toggleReveal = (index: number) => {
    setRevealedIdx((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(index);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const handleAdd = () => {
    setVars([...vars, { key: '', value: '' }]);
  };

  const handleRemove = (index: number) => {
    setVars(vars.filter((_, idx) => idx !== index));
  };

  const handleChange = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...vars];
    updated[index][field] = value;
    setVars(updated);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveEnvVars(
      bot.id,
      vars.filter((v) => v.key.trim() && v.value.trim())
    );
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-[#111726] border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0d121f]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100">{uz.envModalTitle}</h2>
              <p className="text-xs text-slate-400">{bot.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Security Banner */}
        <div className="px-6 py-3 bg-slate-900/90 border-b border-slate-800 text-xs text-slate-300 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>
            {uz.envModalSubtitle}
          </span>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-6 space-y-4 overflow-y-auto flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-slate-200">
              Konfiguratsiya kalitlari ({vars.length})
            </span>
            <button
              type="button"
              onClick={handleAdd}
              className="text-xs font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Yangi kalit</span>
            </button>
          </div>

          <div className="space-y-3">
            {vars.map((v, index) => {
              const isRevealed = Boolean(revealedIdx[index]);
              const isCopied = copiedIdx === index;

              return (
                <div
                  key={index}
                  className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <input
                      type="text"
                      value={v.key}
                      onChange={(e) => handleChange(index, 'key', e.target.value)}
                      placeholder="BOT_TOKEN"
                      className="px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono font-semibold text-emerald-400 focus:outline-none focus:border-emerald-500/50 flex-1"
                    />

                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => toggleReveal(index)}
                        title={isRevealed ? uz.hideSecret : uz.revealSecret}
                        className="p-1.5 text-slate-400 hover:text-slate-200 rounded-md hover:bg-slate-800 transition-colors"
                      >
                        {isRevealed ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>

                      <button
                        type="button"
                        onClick={() => copyToClipboard(v.value, index)}
                        title={uz.copySecret}
                        className="p-1.5 text-slate-400 hover:text-slate-200 rounded-md hover:bg-slate-800 transition-colors"
                      >
                        {isCopied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                      </button>

                      {vars.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemove(index)}
                          className="p-1.5 text-slate-500 hover:text-rose-400 rounded-md hover:bg-slate-800 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="relative">
                    <input
                      type={isRevealed ? 'text' : 'password'}
                      value={v.value}
                      onChange={(e) => handleChange(index, 'value', e.target.value)}
                      placeholder="Kalit qiymati..."
                      className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500/50"
                    />
                    {!isRevealed && (
                      <span className="absolute right-3 top-2 text-[10px] text-slate-500 flex items-center gap-1 pointer-events-none">
                        <Lock className="w-3 h-3 text-slate-500" /> Shifrlangan
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer */}
          <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 rounded-lg transition-colors"
            >
              {uz.cancel}
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-lg shadow-sm transition-all active:scale-95"
            >
              {uz.save}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
