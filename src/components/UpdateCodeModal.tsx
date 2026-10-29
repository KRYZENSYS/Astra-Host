import React, { useState, useRef } from 'react';
import { uz } from '../locales/uz';
import { Bot } from '../types';
import { validateZipFilename, isExtensionAllowed, MAX_ZIP_SIZE_BYTES } from '../lib/botLogic';
import {
  X,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Database,
  RefreshCw,
} from 'lucide-react';

interface UpdateCodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  bot: Bot;
  onUpdateCode: (botId: string, file: File, entrypoint?: string) => void;
}

export const UpdateCodeModal: React.FC<UpdateCodeModalProps> = ({
  isOpen,
  onClose,
  bot,
  onUpdateCode,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [entrypoint, setEntrypoint] = useState(bot.entrypoint || 'main.py');
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileSelect = (file: File) => {
    setError(null);
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError("Faqat ZIP formatidagi arxiv qabul qilinadi.");
      return;
    }
    if (file.size > MAX_ZIP_SIZE_BYTES) {
      setError(`Arxiv hajmi 20 MB dan oshmasligi kerak. Joriy hajm: ${(file.size / (1024 * 1024)).toFixed(1)} MB.`);
      return;
    }
    if (!validateZipFilename(file.name) || !isExtensionAllowed(file.name)) {
      setError("Xavfsizlik xatosi: Arxiv nomi yoki formati xavfli deb topildi.");
      return;
    }

    setSelectedFile(file);
  };

  const handleLoadSampleUpdate = () => {
    const sampleZip = new File(
      [new Uint8Array([80, 75, 3, 4, 10, 0])],
      `${bot.name.toLowerCase().replace(/[^a-z0-9]/g, '_')}_v2.1.0.zip`,
      { type: 'application/zip' }
    );
    setSelectedFile(sampleZip);
    setError(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!selectedFile) {
      setError("Iltimos, yangi ZIP arxivni yuklang yoki namuna paketni tanlang.");
      return;
    }

    onUpdateCode(bot.id, selectedFile, entrypoint.trim() || undefined);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
      <div className="bg-[#111726] border border-slate-800 rounded-2xl w-full max-w-lg flex flex-col shadow-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0d121f]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <RefreshCw className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100">Kodni yangilash</h2>
              <p className="text-xs text-slate-400 font-mono">{bot.name}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Safe Volume Guarantee Notice */}
          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-start gap-2.5 text-xs text-emerald-300">
            <Database className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-100 mb-0.5">/data doimiy hajmi saqlab qolinadi</p>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Yangi kod yuklanganda SQLite ma'lumotlar bazasi va doimiy fayllarga tegilmaydi. Faqat dastur kodi almashtirilib, konteyner qayta yig'iladi.
              </p>
            </div>
          </div>

          {/* 1-click sample / GitHub re-pull */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleLoadSampleUpdate}
              className="flex-1 py-2 px-3 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700/60 rounded-lg text-xs font-medium transition-colors"
            >
              + v2.1.0 yangilanish namunasini tanlash
            </button>
            {bot.sourceType === 'github' && (
              <button
                type="button"
                onClick={() => {
                  const gitZip = new File([new Uint8Array([80, 75, 3, 4])], "github_main_pull.zip", { type: "application/zip" });
                  onUpdateCode(bot.id, gitZip, entrypoint.trim() || undefined);
                  onClose();
                }}
                className="py-2 px-3 bg-indigo-500/15 hover:bg-indigo-500/25 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold transition-colors"
              >
                GitHub git pull
              </button>
            )}
          </div>

          {/* File Upload */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Yangi ZIP arxivni tanlang *
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
            />
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleFileSelect(e.dataTransfer.files[0]);
                }
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
                isDragging
                  ? 'border-emerald-400 bg-emerald-500/5'
                  : 'border-slate-800 hover:border-slate-700 bg-slate-900/50'
              }`}
            >
              <UploadCloud className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              {selectedFile ? (
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-emerald-400 flex items-center justify-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> {selectedFile.name}
                  </p>
                  <p className="text-xs text-slate-400">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-xs font-medium text-slate-200">Yangi ZIP arxivni bu yerga tashlang</p>
                  <p className="text-[11px] text-slate-400 mt-1">Maksimal hajm: 20 MB</p>
                </div>
              )}
            </div>
          </div>

          {/* Entrypoint override */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Ishga tushirish fayli (Entrypoint)
            </label>
            <input
              type="text"
              value={entrypoint}
              onChange={(e) => setEntrypoint(e.target.value)}
              placeholder="main.py yoki bot.py"
              className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
            />
          </div>

          {/* Footer */}
          <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 rounded-lg transition-colors"
            >
              Bekor qilish
            </button>
            <button
              type="submit"
              disabled={!selectedFile}
              className="px-4 py-2 text-xs font-semibold rounded-lg shadow-sm transition-all bg-emerald-400 hover:bg-emerald-300 text-slate-950 disabled:bg-slate-700 disabled:text-slate-400"
            >
              Kodni yangilash va qayta ishga tushirish
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
