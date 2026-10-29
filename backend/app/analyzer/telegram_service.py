import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

TELEGRAM_API_BASE = "https://api.telegram.org"

def validate_bot_token(token: str) -> Dict[str, Any]:
    """
    Validates Telegram bot token against real Telegram API getMe & getWebhookInfo.
    Detects active webhooks that cause HTTP 409 Conflict when running polling bots.
    """
    clean_token = token.strip()
    if not clean_token or ":" not in clean_token:
        return {
            "is_valid": False,
            "error_message": "Bot tokeni noto'g'ri formatda (masalan: 123456789:AAH... formatida bo'lishi kerak).",
            "has_active_webhook": False,
        }

    # 1. Call getMe
    get_me_url = f"{TELEGRAM_API_BASE}/bot{clean_token}/getMe"
    try:
        req = urllib.request.Request(
            get_me_url,
            headers={"User-Agent": "BotHost-Analyzer/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))

        if not res_data.get("ok"):
            return {
                "is_valid": False,
                "error_message": "Telegram API tokenni qabul qilmadi.",
                "has_active_webhook": False,
            }

        bot_info = res_data.get("result", {})
        bot_username = bot_info.get("username", "")
        bot_id = bot_info.get("id")
        first_name = bot_info.get("first_name", "")

    except urllib.error.HTTPError as e:
        if e.code == 401 or e.code == 404:
            return {
                "is_valid": False,
                "error_message": "Token yaroqsiz (401 Unauthorized). Telegram @BotFather bergan tokenni tekshiring.",
                "has_active_webhook": False,
            }
        return {
            "is_valid": False,
            "error_message": f"Telegram API xatoligi (HTTP {e.code}).",
            "has_active_webhook": False,
        }
    except Exception as e:
        # Fallback if internet is temporarily unreachable or blocked in dev sandbox
        return {
            "is_valid": True,  # Allow user to proceed if network is offline
            "offline_mode": True,
            "bot_username": "aniqlanmadi",
            "first_name": "Telegram Bot",
            "has_active_webhook": False,
            "warning": f"Telegram API bilan aloqa o'rnatilmadi ({str(e)}), ammo token formati qabul qilindi.",
        }

    # 2. Check getWebhookInfo
    has_active_webhook = False
    webhook_url = ""
    conflict_warning = None
    try:
        wh_url = f"{TELEGRAM_API_BASE}/bot{clean_token}/getWebhookInfo"
        req = urllib.request.Request(wh_url, headers={"User-Agent": "BotHost-Analyzer/1.0"})
        with urllib.request.urlopen(req, timeout=6) as response:
            wh_data = json.loads(response.read().decode("utf-8"))

        if wh_data.get("ok"):
            wh_result = wh_data.get("result", {})
            webhook_url = wh_result.get("url", "")
            if webhook_url:
                has_active_webhook = True
                conflict_warning = (
                    f"Diqqat: Ushbu botda avval faol webhook sozlangan ({webhook_url}). "
                    "Telegram botlar bir vaqtning o'zida ham Webhook, ham Polling rejimida ishlay olmaydi (HTTP 409 Conflict xatoligi beradi). "
                    "Quyidagi tugma orqali webhookni tozalash tavsiya etiladi."
                )
    except Exception:
        pass

    return {
        "is_valid": True,
        "bot_id": bot_id,
        "username": bot_username,
        "first_name": first_name,
        "has_active_webhook": has_active_webhook,
        "webhook_url": webhook_url,
        "conflict_warning": conflict_warning,
    }


def delete_bot_webhook(token: str, drop_pending_updates: bool = True) -> Dict[str, Any]:
    """Clears existing webhook on Telegram API so polling can start without 409 Conflict."""
    clean_token = token.strip()
    url = f"{TELEGRAM_API_BASE}/bot{clean_token}/deleteWebhook?drop_pending_updates={'true' if drop_pending_updates else 'false'}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BotHost-Analyzer/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
        if res_data.get("ok"):
            return {
                "success": True,
                "message": "Webhook muvaffaqiyatli o'chirildi. Endi bot polling rejimida to'siqsiz ishlaydi."
            }
        desc = res_data.get("description", "Noma'lum xatolik")
        return {
            "success": False,
            "message": f"Webhookni o'chirib bo'lmadi: {desc}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Telegram API xatoligi: {str(e)}"
        }
