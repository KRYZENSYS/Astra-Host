import { PlanType, PlanLimits } from '../types';

export const BANNED_EXTENSIONS = [
  '.exe', '.sh', '.bash', '.bat', '.cmd', '.ps1',
  '.so', '.dll', '.dylib', '.bin', '.elf',
];

export const PLAN_LIMITS: Record<PlanType, PlanLimits> = {
  free: {
    maxBots: 1,
    ramMb: 256,
    cpuQuota: 0.25,
    diskMb: 200,
  },
  paid: {
    maxBots: 5,
    ramMb: 512,
    cpuQuota: 1.0,
    diskMb: 1024,
  },
};

export const MAX_CRASH_RETRIES = 5;
export const MAX_ZIP_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

export function canCreateBot(plan: PlanType, currentCount: number): boolean {
  const limits = PLAN_LIMITS[plan] || PLAN_LIMITS.free;
  return currentCount < limits.maxBots;
}

export function getPlanLimits(plan: PlanType): PlanLimits {
  return PLAN_LIMITS[plan] || PLAN_LIMITS.free;
}

/**
 * Validates against zip-slip path traversal attacks (e.g. `../../etc/passwd` or `/root/.ssh`)
 */
export function validateZipFilename(filename: string): boolean {
  if (!filename || filename.trim() === '') return false;
  const normalized = filename.replace(/\\/g, '/');
  if (normalized.startsWith('/') || normalized.includes('../') || normalized.includes('..\\')) {
    return false;
  }
  return true;
}

/**
 * Validates that file extensions are safe for bot containers
 */
export function isExtensionAllowed(filename: string): boolean {
  const lower = filename.toLowerCase();
  for (const ext of BANNED_EXTENSIONS) {
    if (lower.endsWith(ext)) {
      return false;
    }
  }
  return true;
}

/**
 * Masks secrets at rest so tokens are never exposed in UI or logs
 */
export function maskSecret(value: string): string {
  if (!value) return '';
  return '••••••••••••••••';
}

/**
 * Evaluates crash policy: if consecutive crashes reach 5, halts container permanently
 */
export function evaluateCrashPolicy(
  currentCrashes: number,
  maxAllowed: number = MAX_CRASH_RETRIES
): { shouldHalt: boolean; nextStatus: 'crashed' | 'crashed_stopped'; nextCount: number } {
  const nextCount = currentCrashes + 1;
  if (nextCount >= maxAllowed) {
    return {
      shouldHalt: true,
      nextStatus: 'crashed_stopped',
      nextCount,
    };
  }
  return {
    shouldHalt: false,
    nextStatus: 'crashed',
    nextCount,
  };
}

export function formatUptime(seconds: number): string {
  if (!seconds || seconds <= 0) return '0s';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}k ${hours}s`;
  if (hours > 0) return `${hours}s ${mins}d`;
  return `${mins}d ${seconds % 60}s`;
}
