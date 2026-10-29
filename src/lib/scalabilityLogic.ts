/**
 * Pure testable logic for high-concurrency rate limiting,
 * exponential backoff retry algorithms, and cluster capacity checks.
 */

export interface TokenBucket {
  tokens: number;
  lastRefill: number;
  capacity: number;
  refillRatePerSecond: number;
}

export function createTokenBucket(
  capacity: number,
  refillRatePerSecond: number,
  initialTime: number = Date.now()
): TokenBucket {
  return {
    tokens: capacity,
    lastRefill: initialTime,
    capacity,
    refillRatePerSecond,
  };
}

export function consumeToken(
  bucket: TokenBucket,
  tokensRequested: number = 1,
  now: number = Date.now()
): { allowed: boolean; remainingTokens: number; retryAfterSeconds: number } {
  // Refill tokens based on elapsed time
  const elapsedSeconds = (now - bucket.lastRefill) / 1000;
  if (elapsedSeconds > 0) {
    bucket.tokens = Math.min(bucket.capacity, bucket.tokens + elapsedSeconds * bucket.refillRatePerSecond);
    bucket.lastRefill = now;
  }

  if (bucket.tokens >= tokensRequested) {
    bucket.tokens -= tokensRequested;
    return {
      allowed: true,
      remainingTokens: Math.floor(bucket.tokens),
      retryAfterSeconds: 0,
    };
  }

  const missingTokens = tokensRequested - bucket.tokens;
  const retryAfter = Math.ceil(missingTokens / bucket.refillRatePerSecond);
  return {
    allowed: false,
    remainingTokens: 0,
    retryAfterSeconds: Math.max(1, retryAfter),
  };
}

/**
 * Calculates exponential backoff with bounded cap
 */
export function calculateExponentialBackoff(
  attempt: number,
  baseDelayMs: number = 500,
  maxDelayMs: number = 10000
): number {
  if (attempt <= 0) return baseDelayMs;
  const delay = baseDelayMs * Math.pow(2, attempt - 1);
  return Math.min(delay, maxDelayMs);
}

/**
 * Evaluates crash-loop backoff sequence: 5s, 30s, 120s, then permanent halt
 */
export const CRASH_BACKOFF_SCHEDULE = [5, 30, 120];

export function getCrashBackoffSeconds(crashCount: number): {
  backoffSeconds: number;
  shouldPermanentHalt: boolean;
} {
  if (crashCount <= 0) {
    return { backoffSeconds: 0, shouldPermanentHalt: false };
  }
  if (crashCount > CRASH_BACKOFF_SCHEDULE.length) {
    return { backoffSeconds: 0, shouldPermanentHalt: true };
  }
  return {
    backoffSeconds: CRASH_BACKOFF_SCHEDULE[crashCount - 1],
    shouldPermanentHalt: false,
  };
}

/**
 * Enforces daily restart quota per user (e.g. max 50 restarts/day)
 */
export function canUserRestartBot(dailyRestarts: number, maxDailyAllowed: number = 50): boolean {
  return dailyRestarts < maxDailyAllowed;
}

/**
 * Node capacity scheduler: picks node with lowest memory utilization percentage
 */
export interface ClusterNode {
  id: string;
  name: string;
  totalRamMb: number;
  usedRamMb: number;
  totalCpuCores: number;
  usedCpuCores: number;
  isActive: boolean;
}

export function selectOptimalNode(
  nodes: ClusterNode[],
  requiredRamMb: number,
  requiredCpuCores: number
): ClusterNode | null {
  const eligible = nodes.filter(
    (n) =>
      n.isActive &&
      n.totalRamMb - n.usedRamMb >= requiredRamMb &&
      n.totalCpuCores - n.usedCpuCores >= requiredCpuCores
  );

  if (eligible.length === 0) return null;

  // Sort by lowest RAM utilization ratio
  eligible.sort((a, b) => a.usedRamMb / a.totalRamMb - b.usedRamMb / b.totalRamMb);
  return eligible[0];
}
