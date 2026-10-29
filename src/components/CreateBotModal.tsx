import React, { useState, useRef } from 'react';
import { uz } from '../locales/uz';
import { User } from '../types';
import { canCreateBot, getPlanLimits, validateZipFilename, isExtensionAllowed, MAX_ZIP_SIZE_BYTES } from '../lib/botLogic';
import {
  X,
  UploadCloud,
  FileArchive,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Shield,
  KeyRound,
  FileCode,
} from 'lucide-react';

interface CreateBotModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: User;
  currentBotCount: number;
  onCreateBot: (data: {
    name: string;
    sourceType: 'zip' | 'github';
    sourceUrl?: string;
    entrypoint: string;
    requirementsDetected: boolean;
    envVars: { key: string; value: string }[];
    file?: File;
  }) => void;
}

export const CreateBotModal: React.FC<CreateBotModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  currentBotCount,
  onCreateBot,
}) => {
  const [name, setName] = useState('');
  const [sourceType, setSourceType] = useState<'zip' | 'github'>('zip');
  const [sourceUrl, setSourceUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [detectedEntrypoint, setDetectedEntrypoint] = useState('main.py');
  const [hasRequirements, setHasRequirements] = useState(true);
  const [envVars, setEnvVars] = useState<{ key: string; value: string }[]>([
    { key: 'BOT_TOKEN', value: '' },
    { key: 'DATABASE_PATH', value: '/data/bot.db' },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const limits = getPlanLimits(currentUser.plan);
  const quotaReached = !canCreateBot(currentUser.plan, currentBotCount);

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
    // Suggest bot name from zip name if empty
    if (!name) {
      const suggestedName = file.name
        .replace(/\.zip$/i, '')
        .replace(/[-_]/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
      setName(suggestedName);
    }

    // Auto-detect entrypoint
    const lowerName = file.name.toLowerCase();
    if (lowerName.includes('bot')) {
      setDetectedEntrypoint('bot.py');
    } else if (lowerName.includes('app')) {
      setDetectedEntrypoint('app.py');
    } else {
      setDetectedEntrypoint('main.py');
    }
    setHasRequirements(true);
  };

  const handleAddEnvVar = () => {
    setEnvVars([...envVars, { key: '', value: '' }]);
  };

  const handleRemoveEnvVar = (index: number) => {
    setEnvVars(envVars.filter((_, idx) => idx !== index));
  };

  const handleEnvChange = (index: number, field: 'key' | 'value', val: string) => {
    const updated = [...envVars];
    // Enforce UPPERCASE alphanumeric with underscore for keys
    if (field === 'key') {
      updated[index][field] = val.toUpperCase().replace(/[^A-Z0-9_]/g, '');
    } else {
      updated[index][field] = val;
    }
    setEnvVars(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (quotaReached) {
      setError(uz.errorQuotaExceeded);
      return;
    }

    if (!name.trim()) {
      setError("Iltimos, bot nomini kiriting.");
      return;
    }

    if (sourceType === 'zip' && !selectedFile) {
      setError("Iltimos, bot kodining ZIP arxivini yuklang.");
      return;
    }

    if (sourceType === 'github' && (!sourceUrl.trim() || !sourceUrl.startsWith('http'))) {
      setError("Iltimos, to'g'ri GitHub ombori URL manzilini kiriting (https://github.com/...).");
      return;
    }

    // Validate BOT_TOKEN presence
    const botTokenVar = envVars.find((ev) => ev.key.trim() === 'BOT_TOKEN');
    if (!botTokenVar || !botTokenVar.value.trim()) {
      setError("BOT_TOKEN muhit o'zgaruvchisi kiritilishi shart (Telegram @BotFather tokeni).");
      return;
    }

    onCreateBot({
      name,
      sourceType,
      sourceUrl: sourceType === 'github' ? sourceUrl.trim() : undefined,
      entrypoint: detectedEntrypoint,
      requirementsDetected: hasRequirements,
      envVars: envVars.filter((ev) => ev.key.trim() && ev.value.trim()),
      file: selectedFile || undefined,
    });

    // Reset fields for next time
    setName('');
    setSelectedFile(null);
    setSourceUrl('');
    onClose();
  };

  const loadSampleBot = (type: 'aiogram' | 'telebot') => {
    const dummyZip = new File([new Uint8Array([80, 75, 3, 4, 10, 0])], type === 'aiogram' ? "news_bot.zip" : "support_bot.zip", { type: "application/zip" });
    setSourceType('zip');
    setSelectedFile(dummyZip);
    setName(type === 'aiogram' ? "Tezkor Xabarlar Boti (Aiogram 3)" : "Qo'llab-quvvatlash Boti (Telebot)");
    setDetectedEntrypoint("main.py");
    setHasRequirements(true);
    setEnvVars([
      { key: 'BOT_TOKEN', value: '7481920194:AAHF-EXAMPLE_TELEGRAM_SECRET_KEY' },
      { key: 'DATABASE_PATH', value: '/data/bot.db' },
    ]);
    setError(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
      <div className="bg-[#111726] border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0d121f]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <FileCode className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100">{uz.createBotTitle}</h2>
              <p className="text-xs text-slate-400">{uz.createBotSubtitle}</p>
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto flex-1">
          {quotaReached && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
                <span>
                  Tarif kvotasi: Bepul tarifda 1 ta bot mumkin (sizda {currentBotCount} ta bot bor).
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  import('../lib/store').then(({ botStore }) => {
                    botStore.upgradeToPaid();
                  });
                }}
                className="px-3 py-1.5 bg-gradient-to-r from-amber-500 to-emerald-500 hover:from-amber-400 hover:to-emerald-400 text-slate-950 font-bold rounded-lg text-xs whitespace-nowrap shadow-md transition-all active:scale-95"
              >
                Pro tarifga o'tish (5 bot)
              </button>
            </div>
          )}

          {/* Quick Sample Presets */}
          <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              1-bosishda tayyor namuna bilan to'ldirish:
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => loadSampleBot('aiogram')}
                className="py-1.5 px-3 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700/60 rounded-lg text-xs font-medium transition-colors text-left truncate"
              >
                + Aiogram 3.x namunasi
              </button>
              <button
                type="button"
                onClick={() => loadSampleBot('telebot')}
                className="py-1.5 px-3 bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-slate-700/60 rounded-lg text-xs font-medium transition-colors text-left truncate"
              >
                + Telebot namunasi
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Bot Name */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              {uz.botNameLabel} *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={uz.botNamePlaceholder}
              className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 transition-colors"
            />
          </div>

          {/* Source Type Selector (ZIP vs GitHub) */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              {uz.sourceTypeLabel}
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setSourceType('zip')}
                className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                  sourceType === 'zip'
                    ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {uz.sourceZip}
              </button>
              <button
                type="button"
                onClick={() => setSourceType('github')}
                className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                  sourceType === 'github'
                    ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-300'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {uz.sourceGithub}
              </button>
            </div>
          </div>

          {sourceType === 'github' ? (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                {uz.githubUrlLabel} *
              </label>
              <input
                type="url"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                placeholder={uz.githubUrlPlaceholder}
                className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 font-mono transition-colors"
              />
            </div>
          ) : (
            /* Upload Area for ZIP */
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Python Bot ZIP Arxivini yuklang *
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
                    Hajmi: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-xs font-medium text-slate-200">{uz.dropZipHere}</p>
                  <p className="text-[11px] text-slate-400 mt-1">{uz.zipSizeLimitNotice}</p>
                </div>
              )}
            </div>
          </div>
          )}

          {/* Auto-detected Entrypoint & Container Spec */}
          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">{uz.entrypointLabel}:</span>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={detectedEntrypoint}
                  onChange={(e) => setDetectedEntrypoint(e.target.value)}
                  className="font-mono text-emerald-400 font-semibold bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-xs"
                />
              </div>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Bog'liqliklar:</span>
              <span className="text-slate-300">
                {hasRequirements ? uz.requirementsDetected : uz.requirementsMissing}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Konteyner:</span>
              <span className="text-slate-300">python:3.12-slim (UID:10001 non-root, read-only rootfs)</span>
            </div>
          </div>

          {/* Encrypted Environment Variables */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <KeyRound className="w-4 h-4 text-emerald-400" />
                <label className="text-xs font-semibold text-slate-200">
                  {uz.envVarsSectionTitle}
                </label>
              </div>
              <button
                type="button"
                onClick={handleAddEnvVar}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>O'zgaruvchi qo'shish</span>
              </button>
            </div>
            <p className="text-[11px] text-slate-400 mb-3">{uz.tokenRequiredHint}</p>

            <div className="space-y-2">
              {envVars.map((ev, index) => (
                <div key={index} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={ev.key}
                    onChange={(e) => handleEnvChange(index, 'key', e.target.value)}
                    placeholder="BOT_TOKEN"
                    className="w-1/3 px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500/50"
                  />
                  <input
                    type="password"
                    value={ev.value}
                    onChange={(e) => handleEnvChange(index, 'value', e.target.value)}
                    placeholder={ev.key === 'BOT_TOKEN' ? '7123456789:AAH...' : 'Qiymat...'}
                    className="flex-1 px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-emerald-500/50"
                  />
                  {envVars.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveEnvVar(index)}
                      className="p-2 text-slate-500 hover:text-rose-400 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Hardening Details */}
          <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-[11px] text-emerald-300/90 flex items-start gap-2">
            <Shield className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>
              Xavfsizlik: Konteyner faqat o'qish (read-only rootfs) rejimida ishlaydi. Ma'lumotlar saqlanishi uchun barcha SQLite va sessiya fayllari avtomatik <strong>/data</strong> manziliga yo'naltiriladi.
            </span>
          </div>

          {/* Submit Buttons */}
          <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-800/80">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 rounded-lg transition-colors"
            >
              {uz.cancel}
            </button>
            <button
              type="submit"
              disabled={quotaReached}
              className={`px-4 py-2 text-xs font-semibold rounded-lg shadow-sm transition-all ${
                quotaReached
                  ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                  : 'bg-emerald-400 hover:bg-emerald-300 text-slate-950 active:scale-95'
              }`}
            >
              {uz.createAndDeployBtn}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
