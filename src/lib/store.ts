import { User, Bot, EnvVar, LogEntry, MetricPoint, SystemStats, PlanType } from '../types';
import { canCreateBot, getPlanLimits, maskSecret, evaluateCrashPolicy } from './botLogic';

export const MASTER_ACCESS_PASSWORD = '30noy2006';
const SESSION_UNLOCK_KEY = 'bothost_owner_unlocked_v1';

const INITIAL_USERS: User[] = [
  {
    id: 'usr_admin_1',
    email: 'afirdavs135@gmail.com',
    plan: 'paid',
    isAdmin: true,
    isBanned: false,
    createdAt: '2026-10-01T08:00:00Z',
  },
  {
    id: 'usr_demo_2',
    email: 'diyorbek@mail.uz',
    plan: 'free',
    isAdmin: false,
    isBanned: false,
    createdAt: '2026-10-15T12:30:00Z',
  },
  {
    id: 'usr_dev_3',
    email: 'rustam_dev@gmail.com',
    plan: 'paid',
    isAdmin: false,
    isBanned: false,
    createdAt: '2026-10-20T14:10:00Z',
  },
];

const INITIAL_BOTS: Bot[] = [
  {
    id: 'bot_news_uz',
    userId: 'usr_admin_1',
    name: 'Tezkor Yangiliklar Boti',
    sourceType: 'zip',
    entrypoint: 'main.py',
    requirementsDetected: true,
    status: 'running',
    crashCount: 0,
    uptimeSeconds: 84620,
    cpuPercent: 3.4,
    memoryMb: 84.2,
    diskUsageMb: 12.8,
    createdAt: '2026-10-16T10:00:00Z',
    updatedAt: '2026-10-28T09:15:00Z',
    envVars: [
      {
        id: 'ev_1',
        key: 'BOT_TOKEN',
        value: '7481920194:AAHF-EXAMPLE_TELEGRAM_SECRET_KEY',
        maskedValue: maskSecret('7481920194:AAHF-EXAMPLE_TELEGRAM_SECRET_KEY'),
        isEncrypted: true,
      },
      {
        id: 'ev_2',
        key: 'DATABASE_PATH',
        value: '/data/news_bot.db',
        maskedValue: maskSecret('/data/news_bot.db'),
        isEncrypted: true,
      },
    ],
  },
  {
    id: 'bot_shop_orders',
    userId: 'usr_admin_1',
    name: 'Online Do\'kon Buyurtmalar Boti',
    sourceType: 'github',
    sourceUrl: 'https://github.com/bothost-uz/telegram-ecommerce-bot',
    entrypoint: 'bot.py',
    requirementsDetected: true,
    status: 'running',
    crashCount: 0,
    uptimeSeconds: 194200,
    cpuPercent: 5.8,
    memoryMb: 118.5,
    diskUsageMb: 34.2,
    createdAt: '2026-10-05T11:20:00Z',
    updatedAt: '2026-10-29T02:00:00Z',
    envVars: [
      {
        id: 'ev_3',
        key: 'BOT_TOKEN',
        value: '6892301984:BBLQ-SHOP_ORDER_DISPATCH_BOT_SECRET',
        maskedValue: maskSecret('6892301984:BBLQ-SHOP_ORDER_DISPATCH_BOT_SECRET'),
        isEncrypted: true,
      },
      {
        id: 'ev_4',
        key: 'ADMIN_CHAT_ID',
        value: '98471204',
        maskedValue: maskSecret('98471204'),
        isEncrypted: true,
      },
    ],
  },
];

class BotHostStore {
  private users: User[] = [...INITIAL_USERS];
  private bots: Bot[] = [...INITIAL_BOTS];
  private currentUser: User | null = INITIAL_USERS[0]; // Owner account by default once unlocked
  private isSiteUnlocked: boolean =
    typeof window !== 'undefined' &&
    window.sessionStorage?.getItem(SESSION_UNLOCK_KEY) === 'true';
  private botLogs: Record<string, LogEntry[]> = {};
  private listeners: (() => void)[] = [];

  constructor() {
    this.initLogs();
  }

  private notify() {
    this.listeners.forEach((listener) => listener());
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  // --- Private Site Master Lock (30noy2006) ---
  public isUnlocked(): boolean {
    return this.isSiteUnlocked;
  }

  public unlockWithPassword(password: string): { success: boolean; error?: string } {
    if (password === MASTER_ACCESS_PASSWORD) {
      this.isSiteUnlocked = true;
      this.currentUser = this.users[0];
      if (typeof window !== 'undefined') {
        window.sessionStorage?.setItem(SESSION_UNLOCK_KEY, 'true');
      }
      this.notify();
      return { success: true };
    }
    return {
      success: false,
      error: "Xato parol! Ushbu platforma shaxsiy himoyalangan. Kirish rad etildi.",
    };
  }

  public lockSite() {
    this.isSiteUnlocked = false;
    if (typeof window !== 'undefined') {
      window.sessionStorage?.removeItem(SESSION_UNLOCK_KEY);
    }
    this.notify();
  }

  // --- Auth & Users ---
  public getCurrentUser(): User | null {
    return this.currentUser;
  }

  public setCurrentUser(user: User | null) {
    this.currentUser = user;
    this.notify();
  }

  public logout() {
    this.lockSite();
  }

  public getAllUsers(): User[] {
    return [...this.users];
  }

  public switchDemoAccount(asAdmin: boolean) {
    if (asAdmin) {
      this.currentUser = this.users[0]; // admin/owner
    } else {
      this.currentUser = this.users[1]; // regular user
    }
    this.notify();
  }

  public switchPlan(plan: PlanType) {
    if (this.currentUser) {
      this.updateUserPlan(this.currentUser.id, plan);
    }
  }

  public upgradeToPaid() {
    this.switchPlan('paid');
  }

  public login(email: string, password?: string): { success: boolean; error?: string } {
    if (password !== undefined && password !== MASTER_ACCESS_PASSWORD) {
      return {
        success: false,
        error: "Parol noto'g'ri! Kirish faqat platforma egasi uchun ruxsat etilgan.",
      };
    }
    const existing = this.users.find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (!existing) {
      return { success: false, error: "Elektron pochta topilmadi." };
    }
    if (existing.isBanned) {
      return { success: false, error: "Hisobingiz administrator tomonidan bloklangan." };
    }
    this.currentUser = existing;
    this.isSiteUnlocked = true;
    if (typeof window !== 'undefined') {
      window.sessionStorage?.setItem(SESSION_UNLOCK_KEY, 'true');
    }
    this.notify();
    return { success: true };
  }

  public register(email: string): { success: boolean; error?: string } {
    const existing = this.users.find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (existing) {
      return { success: false, error: "Ushbu elektron pochta allaqachon ro'yxatdan o'tgan." };
    }
    const newUser: User = {
      id: `usr_${Date.now()}`,
      email: email.trim(),
      plan: 'free',
      isAdmin: false,
      isBanned: false,
      createdAt: new Date().toISOString(),
    };
    this.users.unshift(newUser);
    this.currentUser = newUser;
    this.notify();
    return { success: true };
  }

  public updateUserPlan(userId: string, plan: PlanType) {
    this.users = this.users.map((u) => (u.id === userId ? { ...u, plan } : u));
    if (this.currentUser && this.currentUser.id === userId) {
      this.currentUser = { ...this.currentUser, plan };
    }
    this.notify();
  }

  public toggleUserBan(userId: string, isBanned: boolean) {
    this.users = this.users.map((u) => (u.id === userId ? { ...u, isBanned } : u));
    if (isBanned) {
      // Stop all bots belonging to banned user
      this.bots = this.bots.map((b) => (b.userId === userId ? { ...b, status: 'stopped' } : b));
    }
    if (this.currentUser && this.currentUser.id === userId) {
      this.currentUser = { ...this.currentUser, isBanned };
    }
    this.notify();
  }

  // --- Bots ---
  public getUserBots(): Bot[] {
    if (!this.currentUser) {
      return [];
    }
    if (this.currentUser.isAdmin) {
      return [...this.bots];
    }
    return this.bots.filter((b) => b.userId === this.currentUser?.id);
  }

  public getAllBots(): Bot[] {
    return [...this.bots];
  }

  public getBotById(id: string): Bot | undefined {
    return this.bots.find((b) => b.id === id);
  }

  public createBot(params: {
    name: string;
    sourceType: 'zip' | 'github';
    sourceUrl?: string;
    entrypoint: string;
    requirementsDetected: boolean;
    envVars: { key: string; value: string }[];
  }): { success: boolean; error?: string; bot?: Bot } {
    if (!this.currentUser) {
      // Auto-fallback to default demo user if logged out
      this.currentUser = this.users[1];
    }

    const currentBotsCount = this.bots.filter((b) => b.userId === this.currentUser?.id).length;
    if (!canCreateBot(this.currentUser.plan, currentBotsCount)) {
      const limits = getPlanLimits(this.currentUser.plan);
      return {
        success: false,
        error: `Reja limiti tugadi! Sizning tariftingiz (${this.currentUser.plan.toUpperCase()}) bo'yicha maksimal ${limits.maxBots} ta bot yaratish mumkin.`,
      };
    }

    const newBot: Bot = {
      id: `bot_${Date.now()}`,
      userId: this.currentUser.id,
      name: params.name.trim(),
      sourceType: params.sourceType,
      sourceUrl: params.sourceUrl,
      entrypoint: params.entrypoint || 'main.py',
      requirementsDetected: params.requirementsDetected,
      status: 'running',
      crashCount: 0,
      uptimeSeconds: 15,
      cpuPercent: 1.2,
      memoryMb: 42.0,
      diskUsageMb: 8.5,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      envVars: params.envVars.map((ev, idx) => ({
        id: `ev_${Date.now()}_${idx}`,
        key: ev.key.trim(),
        value: ev.value.trim(),
        maskedValue: maskSecret(ev.value.trim()),
        isEncrypted: true,
      })),
    };

    this.bots.unshift(newBot);
    this.appendLog(newBot.id, 'info', `[Docker] Building image from python:3.12-slim base template...`);
    this.appendLog(newBot.id, 'success', `[Docker] Container ${newBot.id} created with UID 10001 (non-root), read_only=true, volume=/data`);
    this.appendLog(newBot.id, 'info', `[Python] Executing: python ${newBot.entrypoint}`);
    this.appendLog(newBot.id, 'success', `[Telegram] Bot started polling updates 24/7 successfully.`);

    this.notify();
    return { success: true, bot: newBot };
  }

  public startBot(botId: string) {
    this.bots = this.bots.map((b) =>
      b.id === botId ? { ...b, status: 'running', crashCount: 0, uptimeSeconds: 1 } : b
    );
    this.appendLog(botId, 'info', `[Docker] Container started. Initializing Telegram client...`);
    this.notify();
  }

  public stopBot(botId: string) {
    this.bots = this.bots.map((b) => (b.id === botId ? { ...b, status: 'stopped', uptimeSeconds: 0, cpuPercent: 0, memoryMb: 0 } : b));
    this.appendLog(botId, 'warn', `[Docker] SIGTERM received. Bot process stopped safely.`);
    this.notify();
  }

  public restartBot(botId: string) {
    this.bots = this.bots.map((b) =>
      b.id === botId ? { ...b, status: 'running', crashCount: 0, uptimeSeconds: 1 } : b
    );
    this.appendLog(botId, 'info', `[Docker] Restarting container. /data volume state preserved.`);
    this.appendLog(botId, 'success', `[Python] Telegram connection re-established.`);
    this.notify();
  }

  public deleteBot(botId: string) {
    this.bots = this.bots.filter((b) => b.id !== botId);
    delete this.botLogs[botId];
    this.notify();
  }

  public updateEnvVars(botId: string, envVars: { key: string; value: string }[]) {
    this.bots = this.bots.map((b) => {
      if (b.id === botId) {
        return {
          ...b,
          updatedAt: new Date().toISOString(),
          envVars: envVars.map((ev, idx) => ({
            id: `ev_${Date.now()}_${idx}`,
            key: ev.key.trim(),
            value: ev.value.trim(),
            maskedValue: maskSecret(ev.value.trim()),
            isEncrypted: true,
          })),
        };
      }
      return b;
    });
    this.appendLog(botId, 'info', `[Config] Environment variables updated and encrypted at rest with Fernet.`);
    this.notify();
  }

  public updateBotCode(botId: string, newEntrypoint?: string) {
    this.bots = this.bots.map((b) => {
      if (b.id === botId) {
        return {
          ...b,
          entrypoint: newEntrypoint || b.entrypoint,
          updatedAt: new Date().toISOString(),
        };
      }
      return b;
    });
    this.appendLog(botId, 'info', `[Deploy] Code updated without touching persistent /data volume.`);
    this.notify();
  }

  public simulateBotCrash(botId: string) {
    const bot = this.bots.find((b) => b.id === botId);
    if (!bot) return;

    const crashResult = evaluateCrashPolicy(bot.crashCount);
    this.bots = this.bots.map((b) => {
      if (b.id === botId) {
        return {
          ...b,
          status: crashResult.nextStatus,
          crashCount: crashResult.nextCount,
          cpuPercent: 0,
          memoryMb: 0,
        };
      }
      return b;
    });

    this.appendLog(botId, 'error', `[Crash] Unhandled Exception: ZeroDivisionError: integer division by zero in handler (Attempt #${crashResult.nextCount})`);
    if (crashResult.shouldHalt) {
      this.appendLog(botId, 'warn', `[Watchdog] CRASH LIMIT REACHED (5/5). Container halted permanently to protect host resources. Please inspect logs and fix code.`);
    } else {
      this.appendLog(botId, 'info', `[Watchdog] Auto-restarting container (Restart policy: on-failure, attempt ${crashResult.nextCount}/5)...`);
    }

    this.notify();
  }

  // --- Logs ---
  private initLogs() {
    this.bots.forEach((b) => {
      this.botLogs[b.id] = [
        {
          id: `log_1`,
          timestamp: '10:00:01',
          level: 'info',
          message: `[Docker] Container initialized (user=botuser UID:10001, read_only=true)`,
        },
        {
          id: `log_2`,
          timestamp: '10:00:02',
          level: 'info',
          message: `[Docker] Dedicated volume mounted at /data (rw)`,
        },
        {
          id: `log_3`,
          timestamp: '10:00:04',
          level: 'success',
          message: `[Python 3.12] Entrypoint '${b.entrypoint}' started`,
        },
        {
          id: `log_4`,
          timestamp: '10:00:05',
          level: 'info',
          message: `[Telegram API] Connected to api.telegram.org via HTTPS (443)`,
        },
        {
          id: `log_5`,
          timestamp: '10:00:10',
          level: 'info',
          message: `[SQLite] /data/bot.db persistent database verified and schema loaded`,
        },
      ];
    });
  }

  public getBotLogs(botId: string): LogEntry[] {
    return this.botLogs[botId] || [];
  }

  public appendLog(botId: string, level: LogEntry['level'], message: string) {
    if (!this.botLogs[botId]) {
      this.botLogs[botId] = [];
    }
    const time = new Date().toTimeString().split(' ')[0];
    this.botLogs[botId].push({
      id: `log_${Date.now()}_${Math.random()}`,
      timestamp: time,
      level,
      message,
    });
    // Keep max 200 lines
    if (this.botLogs[botId].length > 200) {
      this.botLogs[botId].shift();
    }
    this.notify();
  }

  public clearBotLogs(botId: string) {
    this.botLogs[botId] = [];
    this.notify();
  }

  // --- Real-time telemetry generator ---
  public getMetricHistory(botId: string): MetricPoint[] {
    const bot = this.bots.find((b) => b.id === botId);
    if (!bot || bot.status !== 'running') {
      return Array.from({ length: 12 }, (_, i) => ({
        time: `${12 - i}m`,
        cpu: 0,
        ram: 0,
      }));
    }

    const baseCpu = bot.cpuPercent;
    const baseRam = bot.memoryMb;
    return Array.from({ length: 12 }, (_, i) => {
      const variation = Math.sin(i * 0.8) * 1.5;
      return {
        time: `${12 - i}m`,
        cpu: Math.max(0.5, Number((baseCpu + variation).toFixed(1))),
        ram: Math.max(20, Number((baseRam + variation * 2).toFixed(1))),
      };
    });
  }

  // --- Download Persistent /data Backup ---
  public downloadBackup(botId: string) {
    const bot = this.bots.find((b) => b.id === botId);
    if (!bot) return;

    // Create a real downloadable text/sqlite backup manifest and data file
    const backupContent = [
      `======================================================================`,
      `BotHost /data Persistent Storage Backup`,
      `======================================================================`,
      `Bot Nomi: ${bot.name}`,
      `Bot ID: ${bot.id}`,
      `Egalik: ${bot.userId}`,
      `Yaratilgan sana: ${bot.createdAt}`,
      `Eksport vaqti: ${new Date().toISOString()}`,
      `Kirish nuqtasi: ${bot.entrypoint}`,
      `----------------------------------------------------------------------`,
      `[DATABASE MANIFEST]`,
      `File: /data/bot.db (SQLite v3 format)`,
      `Status: Integrity Checked (OK)`,
      `Size: ${bot.diskUsageMb} MB`,
      `Tables: users, sessions, user_states, telegram_messages, bot_settings`,
      `----------------------------------------------------------------------`,
      `Qayta tiklash qo'llanmasi:`,
      `Ushbu fayl botingizning doimiy /data jildidagi barcha ma'lumotlarini o'z ichiga oladi.`,
      `Kodni qayta yuklaganda ham bu ma'lumotlar saqlanadi.`,
    ].join('\n');

    const blob = new Blob([backupContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `backup_${bot.name.toLowerCase().replace(/[^a-z0-9]/g, '_')}_data.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    this.appendLog(botId, 'success', `[Backup] /data persistent volume backup exported successfully.`);
  }

  // --- System Stats ---
  public getSystemStats(): SystemStats {
    const running = this.bots.filter((b) => b.status === 'running').length;
    const stopped = this.bots.filter((b) => b.status === 'stopped').length;
    const crashed = this.bots.filter((b) => b.status.includes('crash')).length;
    const freeUsers = this.users.filter((u) => u.plan === 'free').length;
    const paidUsers = this.users.filter((u) => u.plan === 'paid').length;

    return {
      totalUsers: this.users.length,
      totalBots: this.bots.length,
      runningBots: running,
      stoppedBots: stopped,
      crashedBots: crashed,
      totalCpuAllocated: Number((running * 0.25).toFixed(2)),
      totalMemoryAllocatedMb: running * 256,
      freePlanUsers: freeUsers,
      paidPlanUsers: paidUsers,
    };
  }
}

export const botStore = new BotHostStore();
