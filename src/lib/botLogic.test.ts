import test from 'node:test';
import assert from 'node:assert/strict';
import {
  canCreateBot,
  getPlanLimits,
  validateZipFilename,
  isExtensionAllowed,
  maskSecret,
  evaluateCrashPolicy,
  MAX_CRASH_RETRIES,
} from './botLogic';

test('Plan quota: Free plan enforces maximum 1 bot', () => {
  assert.equal(canCreateBot('free', 0), true);
  assert.equal(canCreateBot('free', 1), false);
  assert.equal(canCreateBot('free', 2), false);

  const limits = getPlanLimits('free');
  assert.equal(limits.maxBots, 1);
  assert.equal(limits.ramMb, 256);
  assert.equal(limits.cpuQuota, 0.25);
});

test('Plan quota: Paid plan enforces maximum 5 bots', () => {
  assert.equal(canCreateBot('paid', 0), true);
  assert.equal(canCreateBot('paid', 4), true);
  assert.equal(canCreateBot('paid', 5), false);

  const limits = getPlanLimits('paid');
  assert.equal(limits.maxBots, 5);
  assert.equal(limits.ramMb, 512);
  assert.equal(limits.cpuQuota, 1.0);
});

test('Zip security: detects and blocks Zip-Slip path traversal', () => {
  assert.equal(validateZipFilename('main.py'), true);
  assert.equal(validateZipFilename('src/bot.py'), true);
  assert.equal(validateZipFilename('utils/sub/helper.py'), true);

  // Dangerous paths
  assert.equal(validateZipFilename('../main.py'), false);
  assert.equal(validateZipFilename('foo/../../etc/passwd'), false);
  assert.equal(validateZipFilename('/root/.bashrc'), false);
  assert.equal(validateZipFilename(''), false);
});

test('Zip security: rejects dangerous binary and shell scripts', () => {
  assert.equal(isExtensionAllowed('bot.py'), true);
  assert.equal(isExtensionAllowed('requirements.txt'), true);
  assert.equal(isExtensionAllowed('config.json'), true);

  // Banned extensions
  assert.equal(isExtensionAllowed('hack.sh'), false);
  assert.equal(isExtensionAllowed('miner.exe'), false);
  assert.equal(isExtensionAllowed('trojan.bat'), false);
  assert.equal(isExtensionAllowed('malicious.so'), false);
});

test('Secret masking: masks sensitive tokens without leaking characters', () => {
  const token = '7123456789:AAH1234567890abcdefghijklmnopqrstuvwxyz';
  const masked = maskSecret(token);
  assert.equal(masked, '••••••••••••••••');
  assert.equal(masked.includes('7123'), false);
  assert.equal(maskSecret(''), '');
});

test('Crash Watchdog: halts container permanently after 5 consecutive crashes', () => {
  // Crashes 1 to 4 should keep restarting
  let state = { crashCount: 0 };
  for (let i = 0; i < MAX_CRASH_RETRIES - 1; i++) {
    const res = evaluateCrashPolicy(state.crashCount);
    assert.equal(res.shouldHalt, false);
    assert.equal(res.nextStatus, 'crashed');
    state.crashCount = res.nextCount;
  }

  // 5th crash must trigger permanent halt
  const finalRes = evaluateCrashPolicy(state.crashCount);
  assert.equal(finalRes.shouldHalt, true);
  assert.equal(finalRes.nextStatus, 'crashed_stopped');
  assert.equal(finalRes.nextCount, 5);
});
