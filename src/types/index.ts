export type PlanType = 'free' | 'paid';

export type BotStatus = 'stopped' | 'running' | 'building' | 'build_failed' | 'error' | 'crashed' | 'crashed_stopped';

export interface User {
  id: string;
  email: string;
  plan: PlanType;
  isAdmin: boolean;
  isBanned: boolean;
  createdAt: string;
}

export interface EnvVar {
  id: string;
  key: string;
  value: string; // Plain value for editing
  maskedValue: string; // Masked value for display
  isEncrypted: boolean;
}

export interface Bot {
  id: string;
  userId: string;
  name: string;
  sourceType: 'zip' | 'github';
  sourceUrl?: string;
  entrypoint: string;
  requirementsDetected: boolean;
  status: BotStatus;
  crashCount: number;
  uptimeSeconds: number;
  cpuPercent: number;
  memoryMb: number;
  diskUsageMb: number;
  createdAt: string;
  updatedAt: string;
  envVars: EnvVar[];
}

export interface PlanLimits {
  maxBots: number;
  ramMb: number;
  cpuQuota: number;
  diskMb: number;
}

export interface SystemStats {
  totalUsers: number;
  totalBots: number;
  runningBots: number;
  stoppedBots: number;
  crashedBots: number;
  totalCpuAllocated: number;
  totalMemoryAllocatedMb: number;
  freePlanUsers: number;
  paidPlanUsers: number;
}

export interface MetricPoint {
  time: string;
  cpu: number;
  ram: number;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
}
