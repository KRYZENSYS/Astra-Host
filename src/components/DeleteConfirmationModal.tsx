import React from 'react';
import { Bot } from '../types';
import { uz } from '../locales/uz';
import { AlertTriangle, Trash2, X } from 'lucide-react';

interface DeleteConfirmationModalProps {
  isOpen: boolean;
  bot: Bot | null;
  onClose: () => void;
  onConfirm: (botId: string) => void;
}

export const DeleteConfirmationModal: React.FC<DeleteConfirmationModalProps> = ({
  isOpen,
  bot,
  onClose,
  onConfirm,
}) => {
  if (!isOpen || !bot) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-[#111726] border border-rose-500/30 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-rose-500/10">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400 border border-rose-500/30">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100">Botni o'chirishni tasdiqlaysizmi?</h2>
              <p className="text-xs text-rose-300/80 font-mono">{bot.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <p className="text-xs text-slate-300 leading-relaxed">
            Haqiqatan ham <strong className="text-white">"{bot.name}"</strong> botini o'chirmoqchimisiz?
          </p>
          <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl space-y-1.5 text-xs text-slate-400">
            <div className="flex items-center gap-2 text-rose-400 font-medium">
              <span>• Docker konteyneri butunlay to'xtatiladi va tozalanadi.</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <span>• /data hajmi va SQLite ma'lumotlar bazasi o'chiriladi.</span>
            </div>
            <div className="flex items-center gap-2 text-emerald-400">
              <span>• Sizning tarif kvotangizda yangi bot uchun joy bo'shaydi.</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-800 bg-[#0d121f]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          >
            {uz.cancel}
          </button>
          <button
            type="button"
            onClick={() => {
              onConfirm(bot.id);
              onClose();
            }}
            className="flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-rose-600/20 transition-all active:scale-95"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Ha, o'chirilsin</span>
          </button>
        </div>
      </div>
    </div>
  );
};
