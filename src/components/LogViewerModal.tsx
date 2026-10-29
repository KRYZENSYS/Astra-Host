import React, { useState, useEffect, useRef } from 'react';
import { Bot, LogEntry } from '../types';
import { botStore } from '../lib/store';
import { uz } from '../locales/uz';
import {
  X,
  Terminal,
  Trash2,
  Download,
  Copy,
  Check,
  Pause,
  Play,
  ArrowDown,
} from 'lucide-react';

interface LogViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  bot: Bot;
}

export const LogViewerModal: React.FC<LogViewerModalProps> = ({
  isOpen,
  onClose,
  bot,
}) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Sync logs and simulate realistic incoming logs if running
  useEffect(() => {
    if (!isOpen) return;
    setLogs(botStore.getBotLogs(bot.id));

    const unsubscribe = botStore.subscribe(() => {
      if (!isPaused) {
        setLogs(botStore.getBotLogs(bot.id));
      }
    });

    // Simulated background log ticker for active bot
    let interval: any = null;
    if (bot.status === 'running' && !isPaused) {
      interval = setInterval(() => {
        const sampleUpdates = [
          `[Telegram API] GET /getUpdates offset=192847 -> 200 OK (0 updates)`,
          `[Dispatcher] Handled incoming message from user @sarvar_99 (chat_id=5819234)`,
          `[SQLite] COMMIT transaction on /data/bot.db (state updated)`,
          `[HealthCheck] Heartbeat OK · Mem: ${bot.memoryMb}MB · PIDs: 14`,
        ];
        const randomMsg = sampleUpdates[Math.floor(Math.random() * sampleUpdates.length)];
        botStore.appendLog(bot.id, 'info', randomMsg);
      }, 4000);
    }

    return () => {
      unsubscribe();
      if (interval) clearInterval(interval);
    };
  }, [bot.id, bot.status, isPaused, isOpen]);

  useEffect(() => {
    if (isOpen && autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll, isOpen]);

  if (!isOpen) return null;

  const handleClear = () => {
    botStore.clearBotLogs(bot.id);
    setLogs([]);
  };

  const handleCopy = () => {
    const text = logs.map((l) => `[${l.timestamp}] ${l.message}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const text = logs.map((l) => `[${l.timestamp}] ${l.message}`).join('\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${bot.name.toLowerCase().replace(/[^a-z0-9]/g, '_')}_logs.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return 'text-rose-400';
      case 'warn':
        return 'text-amber-400';
      case 'success':
        return 'text-emerald-400';
      case 'info':
      default:
        return 'text-slate-300';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0b0f19] border border-slate-800 rounded-2xl w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Terminal Title Bar */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-[#090d16]">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-rose-500/80" />
              <span className="w-3 h-3 rounded-full bg-amber-500/80" />
              <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <span>{bot.name}</span>
              <span className="text-slate-500">·</span>
              <span className="text-slate-400">container://bothost_{bot.id.slice(0, 8)}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`p-1.5 text-xs rounded-lg flex items-center gap-1 border transition-colors ${
                isPaused
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                  : 'bg-slate-800 text-slate-300 border-slate-700/60 hover:text-white'
              }`}
              title={isPaused ? "Davom ettirish" : "To'xtatib turish"}
            >
              {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{isPaused ? "Davom etish" : "Pauza"}</span>
            </button>

            <button
              onClick={() => setAutoScroll(!autoScroll)}
              className={`p-1.5 text-xs rounded-lg flex items-center gap-1 border transition-colors ${
                autoScroll
                  ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                  : 'bg-slate-800 text-slate-400 border-slate-700/60'
              }`}
              title="Avtomatik pastga tushish"
            >
              <ArrowDown className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={handleCopy}
              className="p-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 rounded-lg border border-slate-700/60"
              title="Jurnallardan nusxa olish"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>

            <button
              onClick={handleDownload}
              className="p-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 rounded-lg border border-slate-700/60"
              title="Jurnalni fayl qilib yuklab olish"
            >
              <Download className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={handleClear}
              className="p-1.5 text-xs text-slate-400 hover:text-rose-300 bg-slate-800 rounded-lg border border-slate-700/60"
              title="Jurnallarni tozalash"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 ml-2"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Terminal Screen */}
        <div className="flex-1 p-5 overflow-y-auto font-mono text-xs leading-relaxed space-y-1 terminal-scroll select-text">
          {logs.length === 0 ? (
            <div className="text-slate-500 italic py-8 text-center">
              Hozircha yangi jurnallar mavjud emas. Bot ishga tushirilganda bu yerda xabarlar paydo bo'ladi.
            </div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="flex items-start gap-2.5">
                <span className="text-slate-500 shrink-0 select-none tabular-nums">
                  {log.timestamp}
                </span>
                <span className={`break-all ${getLevelColor(log.level)}`}>
                  {log.message}
                </span>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>

        {/* Status Bar */}
        <div className="px-5 py-2.5 bg-[#090d16] border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${bot.status === 'running' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
            <span>Konteyner: {bot.status.toUpperCase()}</span>
          </div>
          <div className="flex items-center gap-4">
            <span>Satrlar: {logs.length}</span>
            <span>Ulanish: WebSocket/SSE 24/7</span>
          </div>
        </div>
      </div>
    </div>
  );
};
