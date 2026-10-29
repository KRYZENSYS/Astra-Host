import ast
import os
import re
import secrets
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from app.analyzer.models import EnvVarDefinition

TELEGRAM_TOKEN_REGEX = r"^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$"

KNOWN_TOKEN_NAMES = {
    "bot_token", "token", "telegram_token", "api_token", "tg_token", "bot_api_token"
}

KNOWN_SECRET_NAMES = {
    "secret_key", "fernet_key", "encryption_key", "jwt_secret", "app_secret", "hash_salt"
}

KNOWN_PATH_NAMES = {
    "data_dir", "db_path", "database_path", "storage_path", "upload_dir"
}

class EnvVisitor(ast.NodeVisitor):
    def __init__(self):
        self.env_vars: Dict[str, List[str]] = {}  # var_name -> list of locations
        self.sqlite_relative_calls: List[str] = []

    def _add_var(self, name: str, location: str):
        clean_name = name.strip()
        if clean_name and re.match(r"^[A-Z_][A-Z0-9_]*$", clean_name, re.IGNORECASE):
            if clean_name not in self.env_vars:
                self.env_vars[clean_name] = []
            self.env_vars[clean_name].append(location)

    def visit_Subscript(self, node: ast.Subscript):
        # Detect os.environ['KEY']
        try:
            val = node.value
            if isinstance(val, ast.Attribute) and val.attr == "environ":
                if isinstance(val.value, ast.Name) and val.value.id == "os":
                    slice_node = node.slice
                    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                        self._add_var(slice_node.value, f"os.environ['{slice_node.value}'] (qator {node.lineno})")
                    elif isinstance(slice_node, ast.Str):
                        self._add_var(slice_node.s, f"os.environ['{slice_node.s}'] (qator {node.lineno})")
        except Exception:
            pass
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 1. Detect os.getenv('KEY') and os.environ.get('KEY')
        try:
            if isinstance(node.func, ast.Attribute):
                attr_name = node.func.attr
                if attr_name == "getenv":
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        if node.args and isinstance(node.args[0], (ast.Constant, ast.Str)):
                            k = getattr(node.args[0], "value", getattr(node.args[0], "s", None))
                            if k and isinstance(k, str):
                                self._add_var(k, f"os.getenv('{k}') (qator {node.lineno})")
                elif attr_name == "get":
                    val = node.func.value
                    if isinstance(val, ast.Attribute) and val.attr == "environ":
                        if isinstance(val.value, ast.Name) and val.value.id == "os":
                            if node.args and isinstance(node.args[0], (ast.Constant, ast.Str)):
                                k = getattr(node.args[0], "value", getattr(node.args[0], "s", None))
                                if k and isinstance(k, str):
                                    self._add_var(k, f"os.environ.get('{k}') (qator {node.lineno})")

                # 2. Detect sqlite relative calls: sqlite3.connect('...') or aiosqlite.connect('...')
                if attr_name == "connect":
                    func_owner = getattr(node.func.value, "id", None)
                    if func_owner in ["sqlite3", "aiosqlite"]:
                        if node.args and isinstance(node.args[0], (ast.Constant, ast.Str)):
                            db_arg = getattr(node.args[0], "value", getattr(node.args[0], "s", ""))
                            if db_arg and not db_arg.startswith("/") and not db_arg.startswith(":memory:"):
                                self.sqlite_relative_calls.append(f"{func_owner}.connect('{db_arg}') (qator {node.lineno})")

                if attr_name == "create_engine":
                    if node.args and isinstance(node.args[0], (ast.Constant, ast.Str)):
                        url_arg = getattr(node.args[0], "value", getattr(node.args[0], "s", ""))
                        if url_arg.startswith("sqlite:///") and not url_arg.startswith("sqlite:////") and not ":memory:" in url_arg:
                            self.sqlite_relative_calls.append(f"create_engine('{url_arg}') (qator {node.lineno})")
        except Exception:
            pass

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Detect Pydantic BaseSettings / Settings class fields
        is_settings_class = any(
            (isinstance(b, ast.Name) and b.id in ["BaseSettings", "Settings"]) or
            (isinstance(b, ast.Attribute) and b.attr in ["BaseSettings", "Settings"])
            for b in node.bases
        )
        if is_settings_class:
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    var_name = item.target.id
                    self._add_var(var_name, f"Pydantic Settings: {var_name} (qator {item.lineno})")
        self.generic_visit(node)


def analyze_environment_variables(
    project_dir: Path,
    known_names_from_unzip: List[str]
) -> Tuple[List[EnvVarDefinition], Optional[str]]:
    """
    Performs static AST scan across all Python files and merges with discovered .env keys.
    Returns: (list_of_env_definitions, sqlite_warning_if_any)
    """
    py_files = sorted(list(project_dir.glob("*.py"))) + sorted(list(project_dir.rglob("*.py")))

    visitor = EnvVisitor()

    for py_file in py_files:
        try:
            code = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(code, filename=str(py_file))
            visitor.visit(tree)
        except Exception:
            continue

    # Merge variables from .env and AST
    all_discovered_keys: Dict[str, List[str]] = dict(visitor.env_vars)
    for k in known_names_from_unzip:
        if k not in all_discovered_keys:
            all_discovered_keys[k] = [".env faylidan aniqlangan"]
        else:
            all_discovered_keys[k].append(".env faylida mavjud")

    definitions: List[EnvVarDefinition] = []

    # Ensure BOT_TOKEN is present if no token was found
    has_token_var = any(k.lower() in KNOWN_TOKEN_NAMES for k in all_discovered_keys)
    if not has_token_var:
        all_discovered_keys["BOT_TOKEN"] = ["Telegram bot uchun asosiy token"]

    for raw_name, locations in all_discovered_keys.items():
        name = raw_name.strip()
        lower_name = name.lower()

        # Classify variable
        if lower_name in KNOWN_TOKEN_NAMES:
            definitions.append(EnvVarDefinition(
                name=name,
                is_required=True,
                var_type="telegram_token",
                description="Telegram @BotFather tomonidan berilgan bot autentifikatsiya tokeni.",
                default_value=None,
                source_locations=locations,
                suggested_value=None,
                validation_regex=TELEGRAM_TOKEN_REGEX,
            ))
        elif lower_name in KNOWN_SECRET_NAMES or "secret" in lower_name or "key" in lower_name:
            # Auto-generate safe token for secrets
            generated_key = secrets.token_hex(16)
            definitions.append(EnvVarDefinition(
                name=name,
                is_required=False,
                var_type="secret_key",
                description="Xavfsizlik yoki shifrlash kaliti (avtomatik xavfsiz generatsiya qilindi).",
                default_value=generated_key,
                source_locations=locations,
                suggested_value=generated_key,
            ))
        elif lower_name in KNOWN_PATH_NAMES or "dir" in lower_name or "path" in lower_name:
            suggested = "/data" if "dir" in lower_name else "/data/bot.db"
            definitions.append(EnvVarDefinition(
                name=name,
                is_required=False,
                var_type="path",
                description="Doimiy saqlash yo'li (Konteyner qayta ishga tushganda saqlanadi).",
                default_value=suggested,
                source_locations=locations,
                suggested_value=suggested,
            ))
        elif "url" in lower_name or "uri" in lower_name:
            definitions.append(EnvVarDefinition(
                name=name,
                is_required=False,
                var_type="url",
                description="Tashqi xizmat yoki ma'lumotlar bazasi URL manzili.",
                default_value="",
                source_locations=locations,
            ))
        elif lower_name in ["admin_id", "admin_ids", "owner_id", "channel_id", "group_id"]:
            definitions.append(EnvVarDefinition(
                name=name,
                is_required=False,
                var_type="number",
                description="Telegram administrator yoki kanal ID raqami.",
                default_value="",
                source_locations=locations,
            ))
        else:
            definitions.append(EnvVarDefinition(
                name=name,
                is_required=False,
                var_type="string",
                description="Dastur konfiguratsiya o'zgaruvchisi.",
                default_value="",
                source_locations=locations,
            ))

    # Sort so required variables come first
    definitions.sort(key=lambda d: (not d.is_required, d.name))

    # SQLite warning if relative writes detected
    sqlite_warning = None
    if visitor.sqlite_relative_calls:
        locations_str = ", ".join(visitor.sqlite_relative_calls[:3])
        sqlite_warning = (
            f"Bot kodida SQLite bazasi nisbiy yo'lda chaqirilmoqda: {locations_str}. "
            "Konteyner qayta ishga tushganda ma'lumotlar saqlanib qolishi uchun DATA_DIR=/data doimiy hajmiga yo'naltirish tavsiya etiladi."
        )

    return (definitions, sqlite_warning)
