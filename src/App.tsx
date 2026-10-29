import React, { useState, useEffect } from 'react';
import { Bot, User } from './types';
import { botStore } from './lib/store';
import { uz } from './locales/uz';
import { getPlanLimits } from './lib/botLogic';
import { Navbar } from './components/Navbar';
import { BotCard } from './components/BotCard';
import { CreateBotModal } from './components/CreateBotModal';
import { UpdateCodeModal } from './components/UpdateCodeModal';
import { EnvVarsModal } from './components/EnvVarsModal';
import { LogViewerModal } from './components/LogViewerModal';
import { AuthModal } from './components/AuthModal';
import { SmartAnalyzerModal } from './components/SmartAnalyzerModal';
import { DeleteConfirmationModal } from './components/DeleteConfirmationModal';
import {
  Server,
  Plus,
  ShieldCheck,
  HardDrive,
  Cpu,
  Activity,
  CheckCircle2,
  Lock,
  Sparkles,
  KeyRound,
  AlertCircle,
  Users,
  Eye,
  EyeOff,
} from 'lucide-react';

export default function App() {
  const [isUnlocked, setIsUnlocked] = useState<boolean>(botStore.isUnlocked());
  const [masterPasswordInput, setMasterPasswordInput] = useState<string>('');
  const [showMasterPassword, setShowMasterPassword] = useState<boolean>(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);

  const [currentUser, setCurrentUser] = useState<User | null>(botStore.getCurrentUser());
  const [bots, setBots] = useState<Bot[]>(botStore.getUserBots());
  const [allUsers, setAllUsers] = useState<User[]>(botStore.getAllUsers());
  const [activeTab, setActiveTab] = useState<'bots' | 'admin'>('bots');

  // Modals state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSmartAnalyzerOpen, setIsSmartAnalyzerOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [selectedBotForEnv, setSelectedBotForEnv] = useState<Bot | null>(null);
  const [selectedBotForLogs, setSelectedBotForLogs] = useState<Bot | null>(null);
  const [selectedBotForUpdateCode, setSelectedBotForUpdateCode] = useState<Bot | null>(null);
  const [botToDelete, setBotToDelete] = useState<Bot | null>(null);

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Subscribe to store updates
  useEffect(() => {
    const unsubscribe = botStore.subscribe(() => {
      setIsUnlocked(botStore.isUnlocked());
      const user = botStore.getCurrentUser();
      setCurrentUser(user);
      setBots(botStore.getUserBots());
      setAllUsers(botStore.getAllUsers());
    });
    return unsubscribe;
  }, []);

  const handleMasterUnlock = (e: React.FormEvent) => {
    e.preventDefault();
    setUnlockError(null);
    const res = botStore.unlockWithPassword(masterPasswordInput);
    if (res.success) {
      setIsUnlocked(true);
      setMasterPasswordInput('');
      showToast("Xush kelibsiz! Maxfiy egallik qulfi ochildi.");
    } else {
      setUnlockError(res.error || "Parol noto'g'ri! Bu saytdan faqat platforma egasi foydalana oladi.");
    }
  };

  const handleLockSite = () => {
    botStore.lockSite();
    setIsUnlocked(false);
    setMasterPasswordInput('');
    setUnlockError(null);
  };

  const limits = getPlanLimits(currentUser?.plan || 'paid');
  const userBotCount = currentUser ? bots.filter((b) => b.userId === currentUser.id).length : 0;
  const runningCount = bots.filter((b) => b.status === 'running').length;
  const totalAllocatedRam = runningCount * limits.ramMb;
  const sysStats = botStore.getSystemStats();

  const handleStartBot = (id: string) => {
    botStore.startBot(id);
    showToast(uz.successBotStarted);
  };

  const handleStopBot = (id: string) => {
    botStore.stopBot(id);
    showToast(uz.successBotStopped);
  };

  const handleRestartBot = (id: string) => {
    botStore.restartBot(id);
    showToast(uz.successBotRestarted);
  };

  const handleDeleteBot = (id: string) => {
    const target = bots.find((b) => b.id === id);
    if (target) {
      setBotToDelete(target);
    }
  };

  const handleConfirmDelete = (id: string) => {
    botStore.deleteBot(id);
    showToast(uz.successBotDeleted);
    setBotToDelete(null);
  };

  const handleDownloadBackup = (id: string) => {
    botStore.downloadBackup(id);
    showToast(uz.successBackupDownloaded);
  };

  const handleCreateBotSubmit = (data: any) => {
    const res = botStore.createBot(data);
    if (res.success) {
      showToast(uz.successBotCreated);
    } else {
      showToast(res.error || uz.errorQuotaExceeded);
    }
  };

  const handleUpdateBotCode = (botId: string, file: File, entrypoint?: string) => {
    botStore.updateBotCode(botId, entrypoint);
    botStore.appendLog(
      botId,
      'info',
      `[BotHost] Yangi kod yuklandi: ${file.name}. /data hajmi saqlab qolindi.`
    );
    showToast("Yangi kod yuklandi va konteyner qayta ishga tushirildi.");
  };

  const handleSaveEnvVars = (botId: string, envVars: any) => {
    botStore.updateEnvVars(botId, envVars);
    showToast("Muhit o'zgaruvchilari Fernet bilan qayta shifrlab saqlandi.");
  };

  const handleLogout = () => {
    botStore.logout();
    setIsUnlocked(false);
    showToast("Tizimdan chiqildi va sayt qulflandi.");
  };

  // Private Owner Lock Gate: Nobody can enter or use the site without password
  if (!isUnlocked) {
    return (
      <div className="min-h-screen bg-[#070a12] text-slate-100 flex items-center justify-center p-4 selection:bg-emerald-500/20 selection:text-emerald-300">
        <div className="w-full max-w-md bg-[#111726] border border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-6 sm:p-8 space-y-6">
          <div className="flex flex-col items-center text-center space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-lg shadow-emerald-500/10">
              <Lock className="w-7 h-7" />
            </div>
            <div>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 mb-2">
                Shaxsiy Yopiq Tizim
              </span>
              <h1 className="text-xl font-bold text-white tracking-tight">
                BotHost — Maxfiy Kirish Qulfi
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Ushbu platforma shaxsiy hisoblanadi va faqat tizim egasi foydalanishi uchun himoyalangan. Davom etish uchun maxfiy parolni kiriting.
              </p>
            </div>
          </div>

          {unlockError && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{unlockError}</span>
            </div>
          )}

          <form onSubmit={handleMasterUnlock} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Maxfiy kirish paroli *
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
                <input
                  type={showMasterPassword ? 'text' : 'password'}
                  value={masterPasswordInput}
                  onChange={(e) => setMasterPasswordInput(e.target.value)}
                  placeholder="Maxfiy parolni kiriting..."
                  autoFocus
                  className="w-full pl-10 pr-10 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 font-mono transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowMasterPassword(!showMasterPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-white p-0.5"
                >
                  {showMasterPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 bg-emerald-400 hover:bg-emerald-300 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-emerald-500/10 transition-all active:scale-95 flex items-center justify-center gap-2"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Saytni ochish va boshqaruvga kirish</span>
            </button>
          </form>

          <div className="pt-4 border-t border-slate-800/80 text-center">
            <p className="text-[11px] text-slate-500">
              Begona foydalanuvchilar uchun kirish va ro'yxatdan o'tish to'liq yopilgan.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col antialiased selection:bg-emerald-500/20 selection:text-emerald-300">
      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 bg-slate-900/95 border border-emerald-500/40 text-emerald-300 rounded-xl shadow-2xl backdrop-blur-md text-xs font-medium animate-in fade-in slide-in-from-bottom-3">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Bar Navigation */}
      <Navbar
        currentUser={currentUser}
        onOpenCreateBot={() => setIsCreateModalOpen(true)}
        onOpenAnalyzer={() => setIsSmartAnalyzerOpen(true)}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
        onLockSite={handleLockSite}
      />

      {/* Main Content Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <div className="space-y-6">
          {/* Header & KPI Resource Counters */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2.5">
                  <span>{uz.navBots}</span>
                  <span className="text-xs font-mono font-normal px-2.5 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                    {userBotCount} / {limits.maxBots} ta bot
                  </span>
                </h1>

                {currentUser?.isAdmin && (
                  <div className="inline-flex rounded-lg bg-slate-900 p-0.5 border border-slate-800">
                    <button
                      type="button"
                      onClick={() => setActiveTab('bots')}
                      className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
                        activeTab === 'bots'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Botlarim ({userBotCount})
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab('admin')}
                      className={`px-3 py-1 rounded-md text-xs font-semibold flex items-center gap-1.5 transition ${
                        activeTab === 'admin'
                          ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Users className="w-3.5 h-3.5" />
                      {uz.navAdmin}
                    </button>
                  </div>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Har bir bot izolyatsiyalangan Docker konteynerida 24/7 ishlaydi.
              </p>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
              <button
                onClick={() => setIsSmartAnalyzerOpen(true)}
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-500 hover:from-indigo-500 hover:to-emerald-400 rounded-lg shadow-md shadow-indigo-500/20 transition-all whitespace-nowrap active:scale-95"
              >
                <Sparkles className="w-4 h-4 text-emerald-300" />
                <span>Aqlli Tahlilchi va Avto-start</span>
              </button>

              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white border border-slate-700/60 rounded-lg shadow-sm transition-all whitespace-nowrap active:scale-95"
              >
                <Plus className="w-4 h-4" />
                <span>Oddiy yuklash</span>
              </button>
            </div>
          </div>

          {/* Metric KPI cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-[#111726] border border-slate-800 rounded-xl">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span>Mening botlarim</span>
                <Server className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold font-mono tabular-nums text-slate-100">
                {userBotCount} <span className="text-xs text-slate-500 font-normal">/ max {limits.maxBots}</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Tarif:{' '}
                <span className="font-semibold text-emerald-400 uppercase">
                  {currentUser?.plan === 'paid' ? `Pro (${limits.maxBots} bot)` : `Bepul (${limits.maxBots} bot)`}
                </span>
              </div>
            </div>

            <div className="p-4 bg-[#111726] border border-slate-800 rounded-xl">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span>Faol Konteynerlar (24/7)</span>
                <Activity className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-bold font-mono tabular-nums text-slate-100">
                {runningCount}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Docker cgroups izolyatsiyasi
              </div>
            </div>

            <div className="p-4 bg-[#111726] border border-slate-800 rounded-xl">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span>Ajratilgan RAM</span>
                <Cpu className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold font-mono tabular-nums text-slate-100">
                {totalAllocatedRam} <span className="text-xs text-slate-500 font-normal">MB</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                {limits.ramMb} MB har bir bot uchun
              </div>
            </div>

            <div className="p-4 bg-[#111726] border border-slate-800 rounded-xl">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span>Doimiy Hajm (/data)</span>
                <HardDrive className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="text-2xl font-bold font-mono tabular-nums text-slate-100">
                {limits.diskMb} <span className="text-xs text-slate-500 font-normal">MB</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                SQLite va sessiyalar omon qoladi
              </div>
            </div>
          </div>

          {/* Quota reached notice */}
          {userBotCount >= limits.maxBots && (
            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-slate-300">
              <div className="flex items-center gap-3">
                <Lock className="w-4 h-4 text-amber-400 shrink-0" />
                <span>
                  {currentUser?.plan === 'paid'
                    ? "Sizning Pro tarifingizda 5 ta bot kvotasi to'lgan."
                    : "Bepul tarifda 1 ta bot ajratilgan. Ko'proq bot ishga tushirish uchun tarifni oshirishingiz mumkin."}
                </span>
              </div>
              {currentUser?.plan !== 'paid' && (
                <button
                  type="button"
                  onClick={() => {
                    botStore.upgradeToPaid();
                    showToast("Tarifingiz Pro (5 ta bot)ga oshirildi!");
                  }}
                  className="px-3.5 py-1.5 bg-gradient-to-r from-amber-500 to-emerald-500 hover:from-amber-400 hover:to-emerald-400 text-slate-950 font-bold rounded-lg text-xs whitespace-nowrap shadow-md transition-all active:scale-95"
                >
                  Pro tarifga oshirish (5 bot)
                </button>
              )}
            </div>
          )}

          {activeTab === 'admin' && currentUser?.isAdmin ? (
            /* Admin Panel View */
            <div className="bg-[#111726] border border-slate-800 rounded-2xl p-6 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
                <div>
                  <h2 className="text-base font-bold text-white">{uz.adminTitle}</h2>
                  <p className="text-xs text-slate-400">{uz.adminSubtitle}</p>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono text-slate-300">
                  <span>Jami RAM: {sysStats.totalMemoryAllocatedMb} MB</span>
                  <span>Ajratilgan CPU: {sysStats.totalCpuAllocated} vCPU</span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2.5 px-3">Foydalanuvchi</th>
                      <th className="py-2.5 px-3">Tarif</th>
                      <th className="py-2.5 px-3">Holati</th>
                      <th className="py-2.5 px-3 text-right">Amallar</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {allUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-900/40">
                        <td className="py-3 px-3 font-mono text-slate-200">
                          {u.email}
                          {u.isAdmin && (
                            <span className="ml-2 px-2 py-0.5 text-[10px] rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                              Ega / Admin
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                              u.plan === 'paid'
                                ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {u.plan === 'paid' ? 'PRO (5 bot)' : 'BEPUL (1 bot)'}
                          </span>
                        </td>
                        <td className="py-3 px-3">
                          {u.isBanned ? (
                            <span className="text-rose-400 font-medium">Bloklangan</span>
                          ) : (
                            <span className="text-emerald-400 font-medium">Faol</span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-right space-x-2">
                          <button
                            type="button"
                            onClick={() => {
                              const nextPlan = u.plan === 'free' ? 'paid' : 'free';
                              botStore.updateUserPlan(u.id, nextPlan);
                              showToast(`${u.email} tarifi o'zgartirildi.`);
                            }}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
                          >
                            {u.plan === 'free' ? "Pro'ga o'tkazish" : "Bepulga tushirish"}
                          </button>
                          {!u.isAdmin && (
                            <button
                              type="button"
                              onClick={() => {
                                botStore.toggleUserBan(u.id, !u.isBanned);
                                showToast(`${u.email} holati yangilandi.`);
                              }}
                              className="px-2.5 py-1 rounded bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 transition"
                            >
                              {u.isBanned ? 'Blokdan chiqarish' : 'Bloklash'}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : bots.length === 0 ? (
            /* Empty State */
            <div className="p-12 text-center bg-[#111726] border border-slate-800 rounded-2xl space-y-4">
              <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400 mx-auto">
                <Server className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-200">
                  Hozircha botlar mavjud emas
                </h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                  ZIP arxiv yuklang. Docker konteyneri avtomatik yig'iladi va 24/7 ishlaydi.
                </p>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-400 text-slate-950 rounded-lg text-xs font-semibold hover:bg-emerald-300 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Birinchi botni ishga tushirish</span>
              </button>
            </div>
          ) : (
            /* Bots Grid */
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {bots.map((bot) => (
                <BotCard
                  key={bot.id}
                  bot={bot}
                  currentUser={
                    currentUser || {
                      id: 'usr_admin_1',
                      email: 'afirdavs135@gmail.com',
                      plan: 'paid',
                      isAdmin: true,
                      isBanned: false,
                      createdAt: '2026-10-01T10:00:00Z',
                    }
                  }
                  onStart={handleStartBot}
                  onStop={handleStopBot}
                  onRestart={handleRestartBot}
                  onDelete={handleDeleteBot}
                  onOpenLogs={(b) => setSelectedBotForLogs(b)}
                  onOpenEnvVars={(b) => setSelectedBotForEnv(b)}
                  onOpenUpdateCode={(b) => setSelectedBotForUpdateCode(b)}
                  onDownloadBackup={handleDownloadBackup}
                />
              ))}
            </div>
          )}
        </div>

        {/* Security and Acceptable-Use Policy Footer Section */}
        <section
          id="security-policy"
          className="mt-12 p-6 bg-[#111726] border border-slate-800/80 rounded-2xl space-y-4"
        >
          <div className="flex items-center gap-2 text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
            <h3 className="text-sm font-bold text-slate-100">{uz.securityNoticeTitle}</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            {uz.securityNoticeText}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-1">
            <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
              <span className="font-semibold text-slate-200 block mb-1">
                Konteyner Izolyatsiyasi
              </span>
              <span className="text-slate-400 text-[11px]">
                UID 10001 (non-root), read-only rootfs, cap_drop=ALL, pids_limit=100.
              </span>
            </div>
            <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
              <span className="font-semibold text-slate-200 block mb-1">
                Maxfiy Kalitlar
              </span>
              <span className="text-slate-400 text-[11px]">
                BOT_TOKEN va barcha parametrlar Fernet bilan shifrlanadi va jurnallarda ko'rinmaydi.
              </span>
            </div>
            <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
              <span className="font-semibold text-slate-200 block mb-1">
                Doimiy /data Hajmi
              </span>
              <span className="text-slate-400 text-[11px]">
                SQLite fayllari kod yangilanganda ham saqlanib qoladi va zaxiralanadi.
              </span>
            </div>
          </div>
        </section>
      </main>

      {/* Modals */}
      <SmartAnalyzerModal
        isOpen={isSmartAnalyzerOpen}
        onClose={() => setIsSmartAnalyzerOpen(false)}
        currentUserId={currentUser?.id || 'usr_admin_1'}
        onBotCreated={(bot) => {
          const res = botStore.createBot({
            name: bot.name || 'Mening Botim',
            entrypoint: bot.entrypoint || 'main.py',
            sourceType: 'zip',
            requirementsDetected: Boolean(bot.has_requirements),
            envVars: bot.env_vars || [],
          });
          if (res.success) {
            showToast("Bot muvaffaqiyatli tahlil qilindi va ishga tushirildi!");
          } else {
            showToast(res.error || uz.errorQuotaExceeded);
          }
        }}
      />

      <CreateBotModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        currentUser={
          currentUser || {
            id: 'usr_admin_1',
            email: 'afirdavs135@gmail.com',
            plan: 'paid',
            isAdmin: true,
            isBanned: false,
            createdAt: '2026-10-01T10:00:00Z',
          }
        }
        currentBotCount={userBotCount}
        onCreateBot={handleCreateBotSubmit}
      />

      {selectedBotForEnv && (
        <EnvVarsModal
          isOpen={Boolean(selectedBotForEnv)}
          onClose={() => setSelectedBotForEnv(null)}
          bot={selectedBotForEnv}
          onSaveEnvVars={handleSaveEnvVars}
        />
      )}

      {selectedBotForLogs && (
        <LogViewerModal
          isOpen={Boolean(selectedBotForLogs)}
          onClose={() => setSelectedBotForLogs(null)}
          bot={selectedBotForLogs}
        />
      )}

      {selectedBotForUpdateCode && (
        <UpdateCodeModal
          isOpen={Boolean(selectedBotForUpdateCode)}
          onClose={() => setSelectedBotForUpdateCode(null)}
          bot={selectedBotForUpdateCode}
          onUpdateCode={handleUpdateBotCode}
        />
      )}

      <DeleteConfirmationModal
        isOpen={Boolean(botToDelete)}
        bot={botToDelete}
        onClose={() => setBotToDelete(null)}
        onConfirm={handleConfirmDelete}
      />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        currentUser={
          currentUser || {
            id: 'usr_admin_1',
            email: 'afirdavs135@gmail.com',
            plan: 'paid',
            isAdmin: true,
            isBanned: false,
            createdAt: '2026-10-01T10:00:00Z',
          }
        }
        onSuccess={() => showToast("Autentifikatsiya muvaffaqiyatli yakunlandi.")}
      />
    </div>
  );
}
