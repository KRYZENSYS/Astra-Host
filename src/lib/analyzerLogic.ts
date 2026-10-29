/**
 * BotHost Smart Analyzer client-side logic & types.
 * Provides pure deterministic functions for analyzing bot zip contents,
 * evaluating confidence, validating Telegram tokens, and handling auto-fixes.
 */

export interface EntryCandidate {
  filename: string;
  score: number;
  reasons: string[];
  has_main_block?: boolean;
  has_polling?: boolean;
  has_async_run?: boolean;
  is_duplicate_of?: string | null;
  sha256?: string;
}

export interface EnvVarDefinition {
  name: string;
  is_required: boolean;
  var_type: 'telegram_token' | 'secret_key' | 'path' | 'url' | 'number' | 'string';
  description: string;
  default_value?: string | null;
  source_locations?: string[];
  suggested_value?: string | null;
  validation_regex?: string | null;
}

export interface DependencyReport {
  has_requirements_file: boolean;
  declared_packages: string[];
  ast_imported_packages: string[];
  missing_packages: string[];
  recommended_requirements: string;
  system_apt_packages: string[];
  detected_python_version: string;
  reasons: string[];
}

export interface SubProjectInfo {
  relative_path: string;
  name: string;
  entrypoint: string;
  telegram_framework: string;
  confidence: number;
}

export interface AnalysisResult {
  is_supported_language: boolean;
  detected_language: string;
  language_warning?: string | null;
  project_root: string;
  sub_projects: SubProjectInfo[];
  selected_sub_project?: string | null;
  junk_files_cleaned: string[];
  framework: string;
  framework_display_name: string;
  secondary_roles: string[];
  recommended_entrypoint: string;
  entrypoint_candidates: EntryCandidate[];
  dependencies?: DependencyReport;
  env_vars: EnvVarDefinition[];
  sqlite_warning?: string | null;
  confidence_score: number;
  confidence_level: 'high' | 'medium' | 'low';
  warnings: string[];
  dockerfile_content: string;
}

export interface AutoFixAction {
  action_type: 'pip_install' | 'apt_install' | 'missing_env' | 'python_version' | 'permission';
  description: string;
  fixed: boolean;
  detail?: string | null;
}

export const TELEGRAM_TOKEN_REGEX = /^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$/;

/**
 * Validates Telegram bot token format before calling backend getMe.
 */
export function validateTokenFormat(token: string): { isValid: boolean; error?: string } {
  const trimmed = token.trim();
  if (!trimmed) {
    return { isValid: false, error: "Token bo'sh bo'lishi mumkin emas." };
  }
  if (!TELEGRAM_TOKEN_REGEX.test(trimmed)) {
    return {
      isValid: false,
      error: "Token formati noto'g'ri (123456789:AAH... ko'rinishida bo'lishi kerak).",
    };
  }
  return { isValid: true };
}

/**
 * Maps confidence level to Uzbek UI badge properties.
 */
export function getConfidenceBadge(level: 'high' | 'medium' | 'low') {
  switch (level) {
    case 'high':
      return {
        label: "Yuqori ishonchlilik (90%+)",
        colorClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
        icon: "ShieldCheck",
      };
    case 'medium':
      return {
        label: "O'rtacha ishonchlilik (60-89%)",
        colorClass: "bg-amber-500/10 text-amber-400 border-amber-500/30",
        icon: "AlertTriangle",
      };
    case 'low':
    default:
      return {
        label: "Qo'shimcha sozlash talab etiladi (<60%)",
        colorClass: "bg-rose-500/10 text-rose-400 border-rose-500/30",
        icon: "AlertCircle",
      };
  }
}

/**
 * Framework color mapping for badges.
 */
export function getFrameworkBadge(framework: string) {
  if (framework.startsWith('aiogram')) {
    return {
      name: framework === 'aiogram_v3' ? 'aiogram 3.x' : 'aiogram 2.x',
      badgeColor: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    };
  }
  if (framework.startsWith('python_telegram_bot')) {
    return {
      name: framework.includes('v20') ? 'python-telegram-bot v20+' : 'PTB v13',
      badgeColor: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
    };
  }
  if (framework === 'telebot') {
    return {
      name: 'Telebot (pyTelegramBotAPI)',
      badgeColor: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
    };
  }
  if (framework === 'pyrogram') {
    return {
      name: 'Pyrogram',
      badgeColor: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    };
  }
  return {
    name: 'Python Bot',
    badgeColor: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  };
}

/**
 * Filters and classifies environment variables into Required and Optional.
 */
export function categorizeEnvVars(envVars: EnvVarDefinition[]): {
  required: EnvVarDefinition[];
  optional: EnvVarDefinition[];
} {
  const required: EnvVarDefinition[] = [];
  const optional: EnvVarDefinition[] = [];

  for (const ev of envVars) {
    if (ev.is_required) {
      required.push(ev);
    } else {
      optional.push(ev);
    }
  }

  return { required, optional };
}
