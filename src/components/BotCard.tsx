import React, { useState } from 'react';
import { Bot, User } from '../types';
import { uz } from '../locales/uz';
import { getPlanLimits, formatUptime } from '../lib/botLogic';
import { botStore } from '../lib/store';
import {
  Play,
  Square,
  RotateCw,
  Terminal,
  KeyRound,
  Download,
  Trash2,
  FileArchive,
  Database,
  AlertTriangle,
  RefreshCw,
  Activity,
  Zap,
  Github,
} from 'lucide-react';

interface BotCardProps {
  bot: Bot;
  currentUser: User;
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  onRestart: (id: string) => void;
  onDelete: (id: string) => void;
  onOpenLogs: (bot: Bot) => void;
  onOpenEnvVars: (bot: Bot) => void;
  onOpenUpdateCode: (bot: Bot) => void;
  onDownloadBackup: (id: string) => void;
}

export const BotCard: React.FC<BotCardProps> = ({
  bot,
  currentUser,
  onStart,
  onStop,
  onRestart,
  onDelete,
  onOpenLogs,
  onOpenEnvVars,
  onOpenUpdateCode,
  onDownloadBackup,
}) => {
  const [showChart, setShowChart] = useState(false);
  const isRunning = bot.status === 'running';
  const limits = getPlanLimits(currentUser.plan);
  const metricHistory = botStore.getMetricHistory(bot.id);

  const getStatusBadge = () => {
    switch (bot.status) {
      case 'running':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-md">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            {uz.statusRunning}
          </span>
        );
      case 'stopped':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 bg-slate-800/60 border border-slate-700/50 px-2.5 py-1 rounded-md">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            {uz.statusStopped}
          </span>
        );
      case 'crashed':
      case 'crashed_stopped':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2.5 py-1 rounded-md">
            <AlertTriangle className="w-3 h-3" />
            {uz.statusCrashedStopped} (5/5)
          </span>
        );
      case 'building':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-sky-400 bg-sky-500/10 border border-sky-500/20 px-2.5 py-1 rounded-md">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-ping" />
            Yig'ilmoqda...
          </span>
        );
      case 'build_failed':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2.5 py-1 rounded-md">
            <AlertTriangle className="w-3 h-3" />
            Yig'ishda xatolik
          </span>
        );
      case 'error':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-md">
            <AlertTriangle className="w-3 h-3" />
            {uz.statusError}
          </span>
        );
    }
  };

  return (
    <div className="bg-[#111726] border border-slate-800 rounded-xl p-5 hover:border-slate-700/80 transition-all flex flex-col justify-between shadow-sm">
      {/* Top Header */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-slate-800/80 text-emerald-400 border border-slate-700/50">
              {bot.sourceType === 'github' ? (
                <Github className="w-4 h-4 text-indigo-400" />
              ) : (
                <FileArchive className="w-4 h-4" />
              )}
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 text-base tracking-tight leading-snug">
                {bot.name}
              </h3>
              <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5 flex-wrap">
                <span className="font-mono text-slate-300">{bot.entrypoint}</span>
                <span aria-hidden="true">·</span>
                <span>Python 3.12-slim</span>
                <span aria-hidden="true">·</span>
                <span className="flex items-center gap-1 text-emerald-400/90">
                  <Database className="w-3 h-3" /> /data ({bot.diskUsageMb} MB)
                </span>
              </div>
            </div>
          </div>
          <div>{getStatusBadge()}</div>
        </div>

        {/* Crash alert if present */}
        {bot.crashCount > 0 && (
          <div className="mt-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs text-amber-300">
            <span className="flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              Qulashlar: <strong className="font-mono">{bot.crashCount}/5</strong>
            </span>
            <span className="text-[11px] text-amber-400/80">
              {bot.crashCount >= 5 ? "Konteyner to'xtatildi" : "Avtomatik qayta tiklanadi"}
            </span>
          </div>
        )}

        {/* Live Telemetry & Resource Specs */}
        <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-slate-800/70 text-xs text-slate-400">
          <div className="bg-slate-900/60 rounded-lg p-2.5 border border-slate-800/50">
            <span className="block text-[10px] text-slate-500 mb-0.5">{uz.cpuUsage}</span>
            <span className="font-mono text-slate-200 font-semibold">
              {bot.cpuPercent}% <span className="text-[10px] text-slate-500">/ {limits.cpuQuota * 100}%</span>
            </span>
          </div>
          <div className="bg-slate-900/60 rounded-lg p-2.5 border border-slate-800/50">
            <span className="block text-[10px] text-slate-500 mb-0.5">{uz.ramUsage}</span>
            <span className="font-mono text-slate-200 font-semibold">
              {bot.memoryMb} <span className="text-[10px] text-slate-500">/ {limits.ramMb} MB</span>
            </span>
          </div>
          <div className="bg-slate-900/60 rounded-lg p-2.5 border border-slate-800/50">
            <span className="block text-[10px] text-slate-500 mb-0.5">{uz.uptime}</span>
            <span className="font-mono text-emerald-400/90 font-medium">
              {isRunning ? formatUptime(bot.uptimeSeconds) : '0d'}
            </span>
          </div>
        </div>

        {/* Toggleable Live CPU/RAM Mini-Chart */}
        {showChart && (
          <div className="mt-3 p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-cyan-400" />
                Real-vaqt CPU & RAM Telemetriyasi
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => botStore.simulateBotCrash(bot.id)}
                  className="px-2 py-0.5 rounded bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 text-[10px] font-medium flex items-center gap-1 transition"
                >
                  <Zap className="w-3 h-3" />
                  Crash Watchdog sinovi (+1)
                </button>
              </div>
            </div>
            <div className="h-14 flex items-end gap-1 pt-2">
              {metricHistory.map((pt, i) => {
                const heightPct = Math.max(8, Math.min(100, (pt.ram / limits.ramMb) * 100));
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1 group">
                    <div className="w-full bg-slate-900 rounded-t h-10 flex items-end overflow-hidden">
                      <div
                        style={{ height: `${heightPct}%` }}
                        className={`w-full rounded-t transition-all ${
                          isRunning ? 'bg-gradient-to-t from-emerald-500/60 to-cyan-400/80' : 'bg-slate-700'
                        }`}
                        title={`${pt.time}: ${pt.ram} MB RAM, ${pt.cpu}% CPU`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="mt-5 pt-3 border-t border-slate-800/70 flex flex-col gap-2.5">
        {/* Primary Controls (Start / Stop / Restart / Chart / Delete) */}
        <div className="flex items-center gap-2">
          {isRunning ? (
            <button
              type="button"
              onClick={() => onStop(bot.id)}
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-medium text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 transition-all active:scale-95"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>{uz.stopBot}</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onStart(bot.id)}
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-semibold text-slate-950 bg-emerald-400 hover:bg-emerald-300 transition-all active:scale-95 shadow-sm"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{uz.startBot}</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => onRestart(bot.id)}
            title={uz.restartBot}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 border border-slate-700/60 transition-all active:scale-95"
          >
            <RotateCw className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setShowChart(!showChart)}
            title="CPU/RAM grafigi va Watchdog sinovi"
            className={`p-1.5 rounded-lg border transition-all active:scale-95 ${
              showChart
                ? 'text-cyan-300 bg-cyan-500/15 border-cyan-500/40'
                : 'text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 border-slate-700/60'
            }`}
          >
            <Activity className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => onDelete(bot.id)}
            title={uz.deleteBot}
            className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 transition-all active:scale-95"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Secondary Tool Controls */}
        <div className="grid grid-cols-4 gap-1.5 text-center">
          <button
            type="button"
            onClick={() => onOpenLogs(bot)}
            className="flex items-center justify-center gap-1 py-1.5 px-2 rounded-md text-[11px] font-medium text-slate-300 hover:text-white bg-slate-800/50 hover:bg-slate-800 border border-slate-800 transition-all active:scale-95"
          >
            <Terminal className="w-3 h-3 text-emerald-400" />
            <span>Jurnal</span>
          </button>

          <button
            type="button"
            onClick={() => onOpenEnvVars(bot)}
            className="flex items-center justify-center gap-1 py-1.5 px-2 rounded-md text-[11px] font-medium text-slate-300 hover:text-white bg-slate-800/50 hover:bg-slate-800 border border-slate-800 transition-all active:scale-95"
          >
            <KeyRound className="w-3 h-3 text-amber-400" />
            <span>Muhit ({bot.envVars.length})</span>
          </button>

          <button
            type="button"
            onClick={() => onOpenUpdateCode(bot)}
            title="Yangi ZIP yuklash (/data saqlanadi)"
            className="flex items-center justify-center gap-1 py-1.5 px-2 rounded-md text-[11px] font-medium text-slate-300 hover:text-white bg-slate-800/50 hover:bg-slate-800 border border-slate-800 transition-all active:scale-95"
          >
            <RefreshCw className="w-3 h-3 text-sky-400" />
            <span>Yangilash</span>
          </button>

          <button
            type="button"
            onClick={() => onDownloadBackup(bot.id)}
            title="/data arxivini yuklab olish"
            className="flex items-center justify-center gap-1 py-1.5 px-2 rounded-md text-[11px] font-medium text-slate-300 hover:text-white bg-slate-800/50 hover:bg-slate-800 border border-slate-800 transition-all active:scale-95"
          >
            <Download className="w-3 h-3 text-indigo-400" />
            <span>Zaxira</span>
          </button>
        </div>
      </div>
    </div>
  );
};
