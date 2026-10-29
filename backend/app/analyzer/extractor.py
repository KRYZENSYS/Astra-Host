import io
import os
import re
import shutil
import zipfile
from pathlib import Path
from typing import List, Tuple, Set, Dict, Optional

MAX_FILE_COUNT = 2000
MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_RATIO = 100  # Zip-bomb expansion ratio defense

JUNK_DIR_PATTERNS = {
    "__pycache__", ".git", ".github", "tests", "test", ".idea", ".vscode",
    "backups", "backup", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "venv", ".venv", "env", ".env"
}

JUNK_FILE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".log", ".db", ".sqlite", ".sqlite3",
    ".DS_Store", "Thumbs.db", ".orig", ".bak"
}

class SafeExtractionError(Exception):
    pass

def validate_and_extract_safely(
    zip_bytes: bytes,
    target_extract_dir: str
) -> Tuple[str, List[str], List[str]]:
    """
    Validates zip against traversal attacks, zip bombs, and symlinks.
    Extracts into target_extract_dir.
    Returns: (cleaned_project_root, list_of_cleaned_junk_files, list_of_env_variable_names_found)
    """
    target_path = Path(target_extract_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as e:
        raise SafeExtractionError(f"Noto'g'ri yoki buzilgan ZIP arxiv: {str(e)}")

    total_uncompressed_size = 0
    file_count = 0
    zip_size = len(zip_bytes)

    # 1. Validation loop
    for info in zf.infolist():
        file_count += 1
        if file_count > MAX_FILE_COUNT:
            raise SafeExtractionError(f"Arxivdagi fayllar soni cheklovdan oshdi (maksimal {MAX_FILE_COUNT} ta).")

        total_uncompressed_size += info.file_size
        if total_uncompressed_size > MAX_UNCOMPRESSED_SIZE:
            raise SafeExtractionError("Arxiv hajmi ochilganda 100 MB cheklovdan oshib ketdi (Zip-bomb himoyasi).")

        if zip_size > 0 and (total_uncompressed_size / zip_size) > MAX_RATIO:
            raise SafeExtractionError("Shubhali siqish koeffitsienti aniqlandi (Zip-bomb himoyasi).")

        # Zip-slip traversal check
        norm_path = os.path.normpath(info.filename)
        if norm_path.startswith("..") or norm_path.startswith("/") or norm_path.startswith("\\"):
            raise SafeExtractionError(f"Xavfli yo'l aniqlandi (Zip-Slip): {info.filename}")

        # Check for absolute path Windows
        if re.match(r"^[a-zA-Z]:", norm_path):
            raise SafeExtractionError(f"Xavfli mutlaq yo'l aniqlandi: {info.filename}")

        # Symlink check
        is_symlink = (info.external_attr >> 16) & 0o120000 == 0o120000
        if is_symlink:
            raise SafeExtractionError(f"Xavfli simvolik havola (symlink) aniqlandi: {info.filename}")

    # 2. Extract files
    for info in zf.infolist():
        target_file = (target_path / info.filename).resolve()
        if not str(target_file).startswith(str(target_path)):
            raise SafeExtractionError(f"Xavfli yo'l aniqlandi: {info.filename}")

        if info.is_dir():
            target_file.mkdir(parents=True, exist_ok=True)
        else:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as source, open(target_file, "wb") as dest:
                shutil.copyfileobj(source, dest)

    # 3. Detect and unwrap single wrapper folder if exists
    cleaned_root = unwrap_single_folder(target_path)

    # 4. Read .env file for variable names only (NEVER expose or copy user secrets)
    env_var_names = extract_env_variable_names(cleaned_root)

    # 5. Clean junk files and directories
    junk_cleaned = clean_junk(cleaned_root)

    return str(cleaned_root), junk_cleaned, env_var_names


def unwrap_single_folder(dir_path: Path) -> Path:
    """If directory contains only a single subfolder (ignoring __MACOSX), return that subfolder."""
    entries = [p for p in dir_path.iterdir() if p.name != "__MACOSX" and not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir():
        # It's a single wrapper folder
        return entries[0]
    return dir_path


def extract_env_variable_names(dir_path: Path) -> List[str]:
    """Finds .env, .env.example, .env.local, extracts keys only, then deletes sensitive .env files."""
    keys: Set[str] = set()
    for env_file in dir_path.rglob(".env*"):
        try:
            content = env_file.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=", line)
                if match:
                    keys.add(match.group(1))
        except Exception:
            pass

        # If it's a real user .env file (not .example or .sample), remove it so secrets never get baked into image
        if env_file.name in [".env", ".env.local", ".env.production"]:
            try:
                env_file.unlink(missing_ok=True)
            except Exception:
                pass

    return sorted(list(keys))


def clean_junk(dir_path: Path) -> List[str]:
    """Recursively removes junk files, caches, databases, and logs."""
    cleaned: List[str] = []

    for item in list(dir_path.rglob("*")):
        if not item.exists():
            continue

        if item.is_dir():
            if item.name in JUNK_DIR_PATTERNS or item.name.startswith("__pycache__"):
                rel = str(item.relative_to(dir_path))
                try:
                    shutil.rmtree(item, ignore_errors=True)
                    cleaned.append(rel)
                except Exception:
                    pass
        elif item.is_file():
            if item.suffix in JUNK_FILE_EXTENSIONS or item.name in [".DS_Store", "Thumbs.db"]:
                rel = str(item.relative_to(dir_path))
                try:
                    item.unlink(missing_ok=True)
                    cleaned.append(rel)
                except Exception:
                    pass

    return cleaned


def find_sub_projects(root_dir: Path) -> List[Path]:
    """
    Finds subdirectories that look like independent projects (e.g. contain main.py / bot.py or requirements.txt).
    """
    sub_projects: List[Path] = []
    for item in root_dir.iterdir():
        if item.is_dir() and not item.name.startswith(".") and item.name not in JUNK_DIR_PATTERNS:
            has_py = any(item.glob("*.py"))
            has_req = (item / "requirements.txt").is_file()
            if has_py and (has_req or (item / "bot.py").is_file() or (item / "main.py").is_file()):
                sub_projects.append(item)
    return sub_projects
