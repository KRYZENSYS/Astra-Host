import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createTokenBucket,
  consumeToken,
  calculateExponentialBackoff,
  getCrashBackoffSeconds,
  canUserRestartBot,
  selectOptimalNode,
  ClusterNode,
} from './scalabilityLogic';

test('Rate Limiter: Token Bucket allows burst and throttles when depleted', () => {
  const now = 1000000;
  const bucket = createTokenBucket(5, 1, now); // 5 tokens max, 1 token/sec refill

  // Consume 5 allowed tokens
  for (let i = 0; i < 5; i++) {
    const res = consumeToken(bucket, 1, now);
    assert.equal(res.allowed, true);
  }

  // 6th token must be throttled with 429 Retry-After
  const throttled = consumeToken(bucket, 1, now);
  assert.equal(throttled.allowed, false);
  assert.equal(throttled.remainingTokens, 0);
  assert.equal(throttled.retryAfterSeconds >= 1, true);

  // After 2 seconds, 2 tokens should have refilled
  const later = consumeToken(bucket, 1, now + 2000);
  assert.equal(later.allowed, true);
});

test('Queue Retries: Exponential backoff calculates increasing delays capped at maximum', () => {
  assert.equal(calculateExponentialBackoff(1, 500, 5000), 500);   // 500ms
  assert.equal(calculateExponentialBackoff(2, 500, 5000), 1000);  // 1000ms
  assert.equal(calculateExponentialBackoff(3, 500, 5000), 2000);  // 2000ms
  assert.equal(calculateExponentialBackoff(4, 500, 5000), 4000);  // 4000ms
  assert.equal(calculateExponentialBackoff(5, 500, 5000), 5000);  // Capped at 5000ms max
  assert.equal(calculateExponentialBackoff(6, 500, 5000), 5000);
});

test('Crash-Loop Backoff: enforces 5s, 30s, 120s backoff sequence and permanent stop', () => {
  // Crash 1: 5s
  const c1 = getCrashBackoffSeconds(1);
  assert.equal(c1.backoffSeconds, 5);
  assert.equal(c1.shouldPermanentHalt, false);

  // Crash 2: 30s
  const c2 = getCrashBackoffSeconds(2);
  assert.equal(c2.backoffSeconds, 30);
  assert.equal(c2.shouldPermanentHalt, false);

  // Crash 3: 120s (2 minutes)
  const c3 = getCrashBackoffSeconds(3);
  assert.equal(c3.backoffSeconds, 120);
  assert.equal(c3.shouldPermanentHalt, false);

  // Crash 4 (exceeded schedule): permanent stop
  const c4 = getCrashBackoffSeconds(4);
  assert.equal(c4.shouldPermanentHalt, true);
});

test('Quota Enforcement: enforces daily restart limits to prevent restart storms', () => {
  assert.equal(canUserRestartBot(0, 50), true);
  assert.equal(canUserRestartBot(49, 50), true);
  assert.equal(canUserRestartBot(50, 50), false);
  assert.equal(canUserRestartBot(100, 50), false);
});

test('Cluster Scheduler: assigns bot to the least-utilized eligible node', () => {
  const nodes: ClusterNode[] = [
    {
      id: 'node-01',
      name: 'Host 1 (Heavily loaded)',
      totalRamMb: 16384,
      usedRamMb: 14000, // 85% used
      totalCpuCores: 8,
      usedCpuCores: 6,
      isActive: true,
    },
    {
      id: 'node-02',
      name: 'Host 2 (Lightly loaded)',
      totalRamMb: 16384,
      usedRamMb: 4000,  // 24% used
      totalCpuCores: 8,
      usedCpuCores: 2,
      isActive: true,
    },
    {
      id: 'node-03',
      name: 'Host 3 (Offline)',
      totalRamMb: 16384,
      usedRamMb: 0,
      totalCpuCores: 8,
      usedCpuCores: 0,
      isActive: false, // Inactive
    },
  ];

  // Schedule bot requiring 512MB RAM and 1.0 CPU
  const selected = selectOptimalNode(nodes, 512, 1.0);
  assert.notEqual(selected, null);
  assert.equal(selected?.id, 'node-02'); // Must pick node-02 (least utilized)
});
