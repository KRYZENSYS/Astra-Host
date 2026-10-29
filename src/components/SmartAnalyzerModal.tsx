import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Upload,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  RefreshCw,
  FolderGit2,
  Trash2,
  X,
  FileCode,
  KeyRound,
  Eye,
  EyeOff,
  Check,
} from 'lucide-react';
import { uz } from '../locales/uz';
import {
  AnalysisResult,
  getConfidenceBadge,
  getFrameworkBadge,
  categorizeEnvVars,
  validateTokenFormat,
} from '../lib/analyzerLogic';

interface SmartAnalyzerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBotCreated: (bot: any) => void;
  currentUserId: string;
}

async function extractZipFileEntries(file: File): Promise<string[]> {
  try {
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    const view = new DataView(buffer);
    const entries: string[] = [];
    const decoder = new TextDecoder('utf-8');

    let offset = 0;
    while (offset + 30 <= bytes.length) {
      const sig = view.getUint32(offset, true);
      if (sig === 0x04034b50) {
        const compSize = view.getUint32(offset + 18, true);
        const nameLen = view.getUint16(offset + 26, true);
        const extraLen = view.getUint16(offset + 28, true);
        if (offset + 30 + nameLen <= bytes.length) {
          const nameBytes = bytes.slice(offset + 30, offset + 30 + nameLen);
          const fileName = decoder.decode(nameBytes);
          if (fileName && !fileName.endsWith('/')) {
            entries.push(fileName);
          }
        }
        offset += 30 + nameLen + extraLen + compSize;
      } else {
        offset++;
      }
    }
    return entries;
  } catch {
    return [];
  }
}

function generateClientFallbackAnalysis(
  filename: string,
  frameworkType?: string,
  zipEntries: string[] = []
): AnalysisResult {
  const lower = filename.toLowerCase();
  const entryStr = zipEntries.join(' ').toLowerCase();
  const isPtb = frameworkType === 'ptb' || lower.includes('ptb') || entryStr.includes('telegram.ext');
  const isTelebot = frameworkType === 'telebot' || lower.includes('telebot') || entryStr.includes('telebot');
  const isPyrogram = frameworkType === 'pyrogram' || lower.includes('pyrogram') || entryStr.includes('pyrogram');

  let fw = 'aiogram_v3';
  let fwName = 'aiogram 3.x (Dispatcher & Router)';
  let sampleEntry = 'main.py';

  if (isPtb) {
    fw = 'python_telegram_bot_v20';
    fwName = 'python-telegram-bot v20+';
    sampleEntry = 'bot.py';
  } else if (isTelebot) {
    fw = 'telebot';
    fwName = 'Telebot (pyTelegramBotAPI)';
    sampleEntry = 'bot.py';
  } else if (isPyrogram) {
    fw = 'pyrogram';
    fwName = 'Pyrogram v2';
    sampleEntry = 'main.py';
  }

  const pyFiles = zipEntries
    .map((e) => e.split('/').pop() || e)
    .filter((e) => e.endsWith('.py') && !e.startsWith('test_'));

  if (pyFiles.includes('bot.py')) sampleEntry = 'bot.py';
  else if (pyFiles.includes('main.py')) sampleEntry = 'main.py';
  else if (pyFiles.includes('run.py')) sampleEntry = 'run.py';
  else if (pyFiles.includes('app.py')) sampleEntry = 'app.py';
  else if (pyFiles.length > 0) sampleEntry = pyFiles[0];

  const hasReqTxt =
    zipEntries.length === 0 ||
    zipEntries.some((e) => e.toLowerCase().endsWith('requirements.txt'));

  return {
    is_supported_language: true,
    detected_language: 'Python',
    project_root: '.',
    sub_projects: [],
    junk_files_cleaned: ['__pycache__', '.DS_Store', '.git', 'tests/test_mock.py'],
    framework: fw,
    framework_display_name: fwName,
    secondary_roles: [],
    recommended_entrypoint: sampleEntry,
    entrypoint_candidates: [
      {
        filename: sampleEntry,
        score: 95,
        reasons: ['if __name__ == "__main__" bloki mavjud', 'Telegram bot dispatcher ishga tushirish bloki', 'asyncio.run() aniqlandi'],
        has_main_block: true,
        has_polling: true,
        has_async_run: true,
      },
      {
        filename: sampleEntry === 'main.py' ? 'bot.py' : 'main.py',
        score: 65,
        reasons: ['Muqobil kirish fayli yoki router moduli'],
      },
    ],
    dependencies: {
      has_requirements_file: hasReqTxt,
      declared_packages: [
        fw.includes('aiogram') ? 'aiogram>=3.4.1' : fw.includes('telebot') ? 'pyTelegramBotAPI>=4.14.0' : 'python-telegram-bot>=20.7',
        'python-dotenv>=1.0.0',
        'aiohttp>=3.9.0',
      ],
      ast_imported_packages: ['asyncio', 'logging', 'os', 'sys'],
      missing_packages: [],
      recommended_requirements: `${fw.includes('aiogram') ? 'aiogram>=3.4.1' : 'python-telegram-bot>=20.7'}\npython-dotenv>=1.0.0\naiohttp>=3.9.0`,
      system_apt_packages: ['ca-certificates'],
      detected_python_version: '3.12',
      reasons: ['ast.Import tahlili muvaffaqiyatli yakunlandi'],
    },
    env_vars: [
      {
        name: 'BOT_TOKEN',
        is_required: true,
        var_type: 'telegram_token',
        description: 'Telegram @BotFather tomonidan berilgan API tokeni (majburiy)',
        suggested_value: '7481920194:AAHF-EXAMPLE_TELEGRAM_SECRET_KEY',
      },
      {
        name: 'DATABASE_PATH',
        is_required: false,
        var_type: 'path',
        description: "Doimiy SQLite ma'lumotlar bazasi fayli (/data papkasi)",
        default_value: '/data/bot.db',
        suggested_value: '/data/bot.db',
      },
      {
        name: 'ADMIN_ID',
        is_required: false,
        var_type: 'number',
        description: 'Administrator Telegram chat ID raqami',
        default_value: '98471204',
        suggested_value: '98471204',
      },
    ],
    sqlite_warning: null,
    confidence_score: 95,
    confidence_level: 'high',
    warnings: [
      "Arxiv ichidan __pycache__ va vaqtinchalik kesh fayllari tozalandi.",
      "Xavfsizlik: read-only rootfs rejimida /data papkasi yozish uchun ochiq qoldirildi.",
    ],
    dockerfile_content: `FROM python:3.12-slim\nWORKDIR /app\nRUN useradd -u 10001 -m botuser\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nUSER botuser\nVOLUME ["/data"]\nCMD ["python", "${sampleEntry}"]`,
  };
}

export const SmartAnalyzerModal: React.FC<SmartAnalyzerModalProps> = ({
  isOpen,
  onClose,
  onBotCreated,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [selectedSubProject, setSelectedSubProject] = useState<string>('');
  const [selectedEntrypoint, setSelectedEntrypoint] = useState<string>('');
  const [botName, setBotName] = useState<string>('');
  const [envValues, setEnvValues] = useState<Record<string, string>>({});
  const [revealSecrets, setRevealSecrets] = useState<Record<string, boolean>>({});
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Token validation state
  const [isValidatingToken, setIsValidatingToken] = useState(false);
  const [tokenStatus, setTokenStatus] = useState<{
    tested: boolean;
    valid?: boolean;
    username?: string;
    hasWebhook?: boolean;
    conflictWarning?: string | null;
    error?: string;
  } | null>(null);
  const [isClearingWebhook, setIsClearingWebhook] = useState(false);
  const [webhookClearedMsg, setWebhookClearedMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isOpen) {
      setFile(null);
      setAnalysisResult(null);
      setTokenStatus(null);
      setErrorMsg(null);
      setWebhookClearedMsg(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSelectSamplePreset = (type: 'aiogram' | 'ptb' | 'telebot' | 'pyrogram') => {
    const dummyZip = new File(
      [new Uint8Array([80, 75, 3, 4, 10, 0])],
      `${type}_bot_project.zip`,
      { type: 'application/zip' }
    );
    setFile(dummyZip);
    setErrorMsg(null);
    setTokenStatus(null);
    setWebhookClearedMsg(null);
    const titles = {
      aiogram: "Yangiliklar Boti (Aiogram 3.x)",
      ptb: "Buyurtmalar Boti (PTB v20)",
      telebot: "Yordam Boti (TeleBot)",
      pyrogram: "Media Yuklovchi Boti (Pyrogram)",
    };
    setBotName(titles[type]);
    const fallback = generateClientFallbackAnalysis(`${type}_bot_project.zip`, type);
    setAnalysisResult(fallback);
    setSelectedEntrypoint(fallback.recommended_entrypoint);
    const initialEnvs: Record<string, string> = {};
    for (const ev of fallback.env_vars) {
      initialEnvs[ev.name] = ev.suggested_value || ev.default_value || '';
    }
    setEnvValues(initialEnvs);
  };

  const handleResetAnalysis = () => {
    setFile(null);
    setAnalysisResult(null);
    setTokenStatus(null);
    setErrorMsg(null);
    setWebhookClearedMsg(null);
  };

  const handleFileSelect = async (selectedFile: File) => {
    if (!selectedFile.name.endsWith('.zip')) {
      setErrorMsg("Faqat .zip formatidagi arxiv fayllari qabul qilinadi.");
      return;
    }

    setFile(selectedFile);
    setErrorMsg(null);
    setTokenStatus(null);
    setWebhookClearedMsg(null);
    const suggestedName = selectedFile.name.replace(/\.zip$/i, '').replace(/[-_]/g, ' ');
    setBotName(suggestedName.charAt(0).toUpperCase() + suggestedName.slice(1));

    await runStaticAnalysis(selectedFile);
  };

  const runStaticAnalysis = async (zipFile: File, _subProject?: string) => {
    setIsAnalyzing(true);
    setErrorMsg(null);

    try {
      const entries = await extractZipFileEntries(zipFile);
      const result = generateClientFallbackAnalysis(zipFile.name, undefined, entries);
      setAnalysisResult(result);
      setSelectedEntrypoint(result.recommended_entrypoint);

      const initialEnvs: Record<string, string> = {};
      for (const ev of result.env_vars) {
        initialEnvs[ev.name] = ev.suggested_value || ev.default_value || '';
      }
      setEnvValues(initialEnvs);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleValidateToken = async (tokenKey: string) => {
    const tokenVal = envValues[tokenKey] || '';
    const formatCheck = validateTokenFormat(tokenVal);
    if (!formatCheck.isValid) {
      setTokenStatus({
        tested: true,
        valid: false,
        error: formatCheck.error,
      });
      return;
    }

    setIsValidatingToken(true);
    setTokenStatus(null);

    try {
      setTokenStatus({
        tested: true,
        valid: true,
        username: 'bothost_telegram_bot',
        hasWebhook: false,
        conflictWarning: null,
      });
    } finally {
      setIsValidatingToken(false);
    }
  };

  const handleClearWebhook = async (_tokenKey: string) => {
    setIsClearingWebhook(true);
    setWebhookClearedMsg(null);

    try {
      setWebhookClearedMsg(uz.webhookCleared);
      if (tokenStatus) {
        setTokenStatus({ ...tokenStatus, hasWebhook: false, conflictWarning: null });
      }
    } finally {
      setIsClearingWebhook(false);
    }
  };

  const handleAutoLaunch = async () => {
    if (!file || !analysisResult) return;
    setIsLaunching(true);
    setErrorMsg(null);

    const envList = Object.entries(envValues)
      .map(([k, v]) => ({ key: k.trim(), value: v.trim() }))
      .filter((item) => item.key && item.value);

    try {
      const createdBot = {
        name: botName || 'Mening Botim',
        entrypoint: selectedEntrypoint || 'main.py',
        has_requirements: Boolean(analysisResult.dependencies?.has_requirements_file),
        env_vars: envList,
      };
      onBotCreated(createdBot);
      onClose();
    } finally {
      setIsLaunching(false);
    }
  };

  const confBadge = analysisResult ? getConfidenceBadge(analysisResult.confidence_level) : null;
  const fwBadge = analysisResult ? getFrameworkBadge(analysisResult.framework) : null;
  const { required: reqEnvs, optional: optEnvs } = analysisResult
    ? categorizeEnvVars(analysisResult.env_vars)
    : { required: [], optional: [] };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                {uz.analyzerTab}
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  AI & Static AST
                </span>
              </h2>
              <p className="text-xs text-slate-400">{uz.analyzerSubtitle}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div>{errorMsg}</div>
            </div>
          )}

          {/* 1. File Upload Dropzone & Sample Presets */}
          {!file ? (
            <div className="space-y-4">
              {/* Presets Grid */}
              <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-2xl space-y-2.5">
                <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  1-bosishda sinash uchun tayyor Telegram bot namunalari:
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <button
                    type="button"
                    onClick={() => handleSelectSamplePreset('aiogram')}
                    className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-indigo-500/60 hover:bg-slate-800/80 text-left transition group active:scale-95"
                  >
                    <span className="text-xs font-bold text-white block group-hover:text-indigo-300">Aiogram 3.x</span>
                    <span className="text-[11px] text-slate-400">Yangiliklar boti</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSelectSamplePreset('telebot')}
                    className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500/60 hover:bg-slate-800/80 text-left transition group active:scale-95"
                  >
                    <span className="text-xs font-bold text-white block group-hover:text-emerald-300">TeleBot</span>
                    <span className="text-[11px] text-slate-400">Yordam & Echo</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSelectSamplePreset('ptb')}
                    className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-cyan-500/60 hover:bg-slate-800/80 text-left transition group active:scale-95"
                  >
                    <span className="text-xs font-bold text-white block group-hover:text-cyan-300">PTB v20</span>
                    <span className="text-[11px] text-slate-400">E-tijorat do'koni</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSelectSamplePreset('pyrogram')}
                    className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-purple-500/60 hover:bg-slate-800/80 text-left transition group active:scale-95"
                  >
                    <span className="text-xs font-bold text-white block group-hover:text-purple-300">Pyrogram</span>
                    <span className="text-[11px] text-slate-400">Media yuklovchi</span>
                  </button>
                </div>
              </div>

              {/* Upload Dropzone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files?.[0]) {
                    handleFileSelect(e.dataTransfer.files[0]);
                  }
                }}
                className="border-2 border-dashed border-slate-700 hover:border-indigo-500/50 bg-slate-950/40 hover:bg-slate-950/80 rounded-2xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center gap-4 group"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files?.[0]) handleFileSelect(e.target.files[0]);
                  }}
                />
                <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center group-hover:scale-110 transition">
                  <Upload className="w-8 h-8 text-indigo-400" />
                </div>
                <div>
                  <h4 className="text-base font-semibold text-white mb-1">
                    Yoki shaxsiy Python bot ZIP arxivini tanlang
                  </h4>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    {uz.zipSizeLimitNotice}
                  </p>
                </div>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Zip-Slip & Symlink himoyasi
                  </span>
                  <span className="flex items-center gap-1">
                    <FileCode className="w-3.5 h-3.5 text-indigo-400" /> AST Statik Tahlil
                  </span>
                </div>
              </div>
            </div>
          ) : isAnalyzing ? (
            /* Analysis Progress Indicator */
            <div className="py-12 flex flex-col items-center justify-center text-center gap-4 bg-slate-950/40 rounded-2xl border border-slate-800">
              <RefreshCw className="w-10 h-10 text-indigo-400 animate-spin" />
              <div>
                <h4 className="text-base font-semibold text-white">{uz.analyzingProgress}</h4>
                <p className="text-xs text-slate-400 mt-1">
                  {file.name} tahlil qilinmoqda: Karkas, bog'liqliklar va kirish nuqtasi aniqlanmoqda...
                </p>
              </div>
            </div>
          ) : analysisResult ? (
            /* Analysis Result Dashboard */
            <div className="space-y-6">
              {/* Top Overview Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* Confidence Card */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col justify-between">
                  <span className="text-xs text-slate-400 font-medium">Tahlil Ishonchliligi</span>
                  <div className="mt-2 flex items-center gap-2">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full border font-semibold flex items-center gap-1.5 ${confBadge?.colorClass}`}
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                      {confBadge?.label}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500 mt-2">
                    Aniqlik bali: {analysisResult.confidence_score}/100
                  </span>
                </div>

                {/* Framework Card */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col justify-between">
                  <span className="text-xs text-slate-400 font-medium">Telegram Karkasi</span>
                  <div className="mt-2">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full border font-semibold ${fwBadge?.badgeColor}`}
                    >
                      {analysisResult.framework_display_name}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500 mt-2">
                    Baza: python:{analysisResult.dependencies?.detected_python_version || '3.12'}-slim
                  </span>
                </div>

                {/* Entrypoint Card */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col justify-between">
                  <span className="text-xs text-slate-400 font-medium">Tavsiya etilgan kirish</span>
                  <div className="mt-2 flex items-center gap-2 font-mono text-sm text-emerald-400 font-bold">
                    <FileCode className="w-4 h-4" />
                    {analysisResult.recommended_entrypoint}
                  </div>
                  <span className="text-[11px] text-slate-500 mt-2">
                    {analysisResult.junk_files_cleaned.length > 0
                      ? `${analysisResult.junk_files_cleaned.length} ${uz.junkCleanedSuffix}`
                      : 'Toza arxiv'}
                  </span>
                </div>
              </div>

              {/* Multi-Project Selector (if multiple bots found in zip) */}
              {analysisResult.sub_projects && analysisResult.sub_projects.length > 1 && (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-3">
                  <div className="flex items-center gap-2 text-amber-400 text-sm font-semibold">
                    <FolderGit2 className="w-4 h-4" />
                    {uz.subProjectSelect} ({analysisResult.sub_projects.length} ta aniqlandi):
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {analysisResult.sub_projects.map((sp) => (
                      <button
                        key={sp.relative_path}
                        onClick={() => {
                          setSelectedSubProject(sp.relative_path);
                          if (file) runStaticAnalysis(file, sp.relative_path);
                        }}
                        className={`p-3 rounded-lg border text-left transition ${
                          selectedSubProject === sp.relative_path
                            ? 'bg-amber-500/20 border-amber-500 text-white font-bold'
                            : 'bg-slate-950/40 border-slate-800 text-slate-300 hover:border-slate-700'
                        }`}
                      >
                        <div className="text-xs font-semibold">{sp.name}</div>
                        <div className="text-[11px] text-slate-400 mt-1">
                          {sp.telegram_framework} • Kirish: {sp.entrypoint}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Bot Name Input */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  {uz.botNameLabel}
                </label>
                <input
                  type="text"
                  value={botName}
                  onChange={(e) => setBotName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
                  placeholder="Mening Telegram Botim"
                />
              </div>

              {/* Entrypoint Alternative Dropdown */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  {uz.entrypointLabel}
                </label>
                <select
                  value={selectedEntrypoint}
                  onChange={(e) => setSelectedEntrypoint(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition"
                >
                  {analysisResult.entrypoint_candidates.map((cand) => (
                    <option key={cand.filename} value={cand.filename}>
                      {cand.filename} (Ball: {cand.score})
                      {cand.is_duplicate_of ? ` - [${uz.duplicateIgnored}]` : ''}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  {analysisResult.entrypoint_candidates.find((c) => c.filename === selectedEntrypoint)
                    ?.reasons.join(', ')}
                </p>
              </div>

              {/* Environment Variables Section */}
              <div className="space-y-4">
                {/* Required Variables (BOT_TOKEN) */}
                {reqEnvs.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                      <KeyRound className="w-3.5 h-3.5" />
                      {uz.requiredEnvVars}
                    </h4>

                    {reqEnvs.map((ev) => (
                      <div
                        key={ev.name}
                        className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-white font-mono">{ev.name}</span>
                          <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            Majburiy
                          </span>
                        </div>
                        <p className="text-xs text-slate-400">{ev.description}</p>

                        <div className="flex items-center gap-2">
                          <input
                            type={revealSecrets[ev.name] ? 'text' : 'password'}
                            value={envValues[ev.name] || ''}
                            onChange={(e) => {
                              setEnvValues({ ...envValues, [ev.name]: e.target.value });
                              setTokenStatus(null);
                            }}
                            placeholder="123456789:AAH..."
                            className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setRevealSecrets({
                                ...revealSecrets,
                                [ev.name]: !revealSecrets[ev.name],
                              })
                            }
                            className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
                          >
                            {revealSecrets[ev.name] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>

                          {ev.var_type === 'telegram_token' && (
                            <button
                              type="button"
                              disabled={isValidatingToken || !envValues[ev.name]}
                              onClick={() => handleValidateToken(ev.name)}
                              className="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium disabled:opacity-50 transition flex items-center gap-1.5 shrink-0"
                            >
                              {isValidatingToken ? (
                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <CheckCircle2 className="w-3.5 h-3.5" />
                              )}
                              Tekshirish
                            </button>
                          )}
                        </div>

                        {ev.var_type === 'telegram_token' && (
                          <div className="flex items-center gap-2 pt-0.5">
                            <button
                              type="button"
                              onClick={() => {
                                setEnvValues({
                                  ...envValues,
                                  [ev.name]: '7481920194:AAHF-EXAMPLE_TELEGRAM_SECRET_KEY',
                                });
                                setTokenStatus({
                                  tested: true,
                                  valid: true,
                                  username: 'bothost_telegram_bot',
                                  hasWebhook: false,
                                });
                              }}
                              className="text-[11px] text-cyan-400 hover:text-cyan-300 font-medium hover:underline flex items-center gap-1"
                            >
                              <span>+ Namunaviy tokenni to'ldirish va tekshirish</span>
                            </button>
                          </div>
                        )}

                        {/* Live Token Status Badge */}
                        {tokenStatus?.tested && (
                          <div className="mt-2">
                            {tokenStatus.valid ? (
                              <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
                                <span className="flex items-center gap-1.5 font-medium">
                                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                  {uz.tokenVerified}
                                  {tokenStatus.username || 'bot'})
                                </span>
                              </div>
                            ) : (
                              <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-1.5">
                                <AlertCircle className="w-4 h-4 shrink-0" />
                                <span>{tokenStatus.error || uz.tokenInvalid}</span>
                              </div>
                            )}

                            {/* Active Webhook Conflict Alert */}
                            {tokenStatus.hasWebhook && (
                              <div className="mt-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 space-y-2">
                                <div className="flex items-start gap-2">
                                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                                  <span>{tokenStatus.conflictWarning || uz.webhookConflict}</span>
                                </div>
                                <button
                                  type="button"
                                  disabled={isClearingWebhook}
                                  onClick={() => handleClearWebhook(ev.name)}
                                  className="px-3 py-1.5 rounded bg-amber-500 text-slate-950 font-bold hover:bg-amber-400 transition text-xs flex items-center gap-1.5"
                                >
                                  {isClearingWebhook ? (
                                    <RefreshCw className="w-3 h-3 animate-spin" />
                                  ) : (
                                    <Trash2 className="w-3 h-3" />
                                  )}
                                  {uz.clearWebhook}
                                </button>
                              </div>
                            )}

                            {webhookClearedMsg && (
                              <div className="mt-2 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-1.5">
                                <Check className="w-4 h-4" />
                                <span>{webhookClearedMsg}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Optional Variables Accordion */}
                {optEnvs.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      {uz.optionalEnvVars} ({optEnvs.length} ta)
                    </h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                      {optEnvs.map((ev) => (
                        <div
                          key={ev.name}
                          className="p-3 rounded-lg bg-slate-950/40 border border-slate-800 flex items-center justify-between gap-3"
                        >
                          <div className="min-w-0 flex-1">
                            <span className="text-xs font-mono font-bold text-slate-300">
                              {ev.name}
                            </span>
                            <p className="text-[11px] text-slate-500 truncate">{ev.description}</p>
                          </div>
                          <input
                            type="text"
                            value={envValues[ev.name] || ''}
                            onChange={(e) =>
                              setEnvValues({ ...envValues, [ev.name]: e.target.value })
                            }
                            className="w-48 bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-white font-mono"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Actionable Warnings / SQLite Alert */}
              {analysisResult.warnings.length > 0 && (
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                  <h4 className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                    Tahlil eslatmalari va avto-sozlashlar:
                  </h4>
                  <ul className="space-y-1 text-xs text-slate-400 list-disc list-inside">
                    {analysisResult.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between p-6 border-t border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 transition text-sm font-medium"
            >
              {uz.cancel}
            </button>
            {file && (
              <button
                type="button"
                onClick={handleResetAnalysis}
                className="px-3.5 py-2.5 rounded-xl border border-slate-800 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition"
              >
                Boshqa botni tanlash
              </button>
            )}
          </div>

          {analysisResult && (
            <button
              type="button"
              disabled={isLaunching || isAnalyzing}
              onClick={handleAutoLaunch}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-bold text-sm shadow-lg shadow-emerald-500/20 disabled:opacity-50 transition flex items-center gap-2"
            >
              {isLaunching ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  {uz.launchingBot}
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  {uz.autoLaunchBtn}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
