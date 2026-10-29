import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  validateTokenFormat,
  getConfidenceBadge,
  getFrameworkBadge,
  categorizeEnvVars,
  EnvVarDefinition,
} from './analyzerLogic.js';

describe('AnalyzerLogic client tests', () => {
  it('validates correct Telegram bot token format', () => {
    const validToken = '123456789:AAHabcdefghijklmnopqrstuvwxyz123456';
    const res = validateTokenFormat(validToken);
    assert.equal(res.isValid, true);
    assert.equal(res.error, undefined);
  });

  it('rejects invalid Telegram bot token formats', () => {
    assert.equal(validateTokenFormat('').isValid, false);
    assert.equal(validateTokenFormat('12345:short').isValid, false);
    assert.equal(validateTokenFormat('no_colon_token_here_random_1234567890').isValid, false);
  });

  it('provides Uzbek confidence badges', () => {
    const high = getConfidenceBadge('high');
    assert.match(high.label, /Yuqori ishonchlilik/);
    assert.match(high.colorClass, /emerald/);

    const med = getConfidenceBadge('medium');
    assert.match(med.label, /O'rtacha ishonchlilik/);

    const low = getConfidenceBadge('low');
    assert.match(low.label, /Qo'shimcha sozlash/);
  });

  it('maps framework badges accurately', () => {
    assert.equal(getFrameworkBadge('aiogram_v3').name, 'aiogram 3.x');
    assert.equal(getFrameworkBadge('telebot').name, 'Telebot (pyTelegramBotAPI)');
    assert.match(getFrameworkBadge('python_telegram_bot_v20').name, /python-telegram-bot v20/);
  });

  it('categorizes required and optional env vars', () => {
    const mockVars: EnvVarDefinition[] = [
      {
        name: 'BOT_TOKEN',
        is_required: true,
        var_type: 'telegram_token',
        description: 'Telegram Bot Token',
      },
      {
        name: 'SECRET_KEY',
        is_required: false,
        var_type: 'secret_key',
        description: 'Secret Key',
      },
      {
        name: 'DATA_DIR',
        is_required: false,
        var_type: 'path',
        description: 'Data Dir',
      },
    ];

    const { required, optional } = categorizeEnvVars(mockVars);
    assert.equal(required.length, 1);
    assert.equal(required[0].name, 'BOT_TOKEN');
    assert.equal(optional.length, 2);
    assert.equal(optional[0].name, 'SECRET_KEY');
    assert.equal(optional[1].name, 'DATA_DIR');
  });
});
