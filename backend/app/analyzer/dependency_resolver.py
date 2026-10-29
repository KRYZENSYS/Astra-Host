import ast
import re
from pathlib import Path
from typing import Set, List, Dict, Tuple
from app.analyzer.models import DependencyReport

# Comprehensive Python Standard Library modules to never include in requirements.txt
STDLIB_MODULES = {
    "abc", "argparse", "array", "ast", "asynchat", "asyncio", "asyncore",
    "atexit", "base64", "binascii", "binhex", "bisect", "builtins", "bz2",
    "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code", "codecs",
    "codeop", "collections", "colorsys", "compileall", "concurrent",
    "configparser", "contextlib", "contextvars", "copy", "copyreg", "crypt",
    "csv", "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings", "enum",
    "errno", "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
    "formatter", "fpectl", "fractions", "ftplib", "functools", "gc", "getopt",
    "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "imaplib", "imghdr", "imp", "importlib",
    "inspect", "io", "ipaddress", "itertools", "json", "keyword", "lib2to3",
    "linecache", "locale", "logging", "lzma", "mailbox", "mailcap", "marshal",
    "math", "mimetypes", "mmap", "modulefinder", "msilib", "msvcrt", "multiprocessing",
    "netrc", "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev",
    "parser", "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
    "platform", "plistlib", "poplib", "posix", "posixpath", "pprint",
    "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc",
    "queue", "quopri", "random", "re", "readline", "reprlib", "resource",
    "rlcompleter", "runpy", "sched", "secrets", "select", "selectors",
    "shelve", "shlex", "shutil", "signal", "site", "smtpd", "smtplib",
    "sndhdr", "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat",
    "statistics", "string", "stringprep", "struct", "subprocess", "sunau",
    "symbol", "symtable", "sys", "sysconfig", "syslog", "tabnanny", "tarfile",
    "telnetlib", "tempfile", "termios", "test", "textwrap", "threading",
    "time", "timeit", "tkinter", "token", "tokenize", "trace", "traceback",
    "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing",
    "unicodedata", "unittest", "urllib", "uu", "uuid", "venv", "warnings",
    "wave", "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
    "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
    "zoneinfo",
}

# Module import name -> PyPI package name
IMPORT_TO_PYPI: Dict[str, str] = {
    "telebot": "pyTelegramBotAPI",
    "PIL": "pillow",
    "cv2": "opencv-python-headless",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "telegram": "python-telegram-bot",
    "dateutil": "python-dateutil",
    "psycopg2": "psycopg2-binary",
    "fitz": "PyMuPDF",
    "docx": "python-docx",
    "magic": "python-magic",
    "sklearn": "scikit-learn",
    "sqlalchemy": "sqlalchemy",
    "aiohttp": "aiohttp",
    "requests": "requests",
    "httpx": "httpx",
    "pydantic": "pydantic",
    "pydantic_settings": "pydantic-settings",
    "apscheduler": "apscheduler",
    "aiosqlite": "aiosqlite",
    "aioredis": "redis",
    "redis": "redis",
    "qrcode": "qrcode",
    "openai": "openai",
    "google": "google-genai",
    "google_genai": "google-genai",
    "asyncpg": "asyncpg",
    "alembic": "alembic",
    "pyrogram": "pyrogram",
    "telethon": "telethon",
    "aiogram": "aiogram",
    "cryptography": "cryptography",
    "jwt": "PyJWT",
    "jose": "python-jose",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "flask": "flask",
    "openpyxl": "openpyxl",
    "pandas": "pandas",
    "numpy": "numpy",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
}

# Package -> required Debian/Ubuntu apt-get packages
SYSTEM_APT_PACKAGES: Dict[str, List[str]] = {
    "opencv-python": ["libgl1", "libglib2.0-0"],
    "opencv-python-headless": ["libglib2.0-0"],
    "pillow": ["libjpeg-dev", "zlib1g-dev", "libfreetype6-dev"],
    "pymupdf": ["libmupdf-dev"],
    "pydub": ["ffmpeg"],
    "lxml": ["libxml2-dev", "libxslt1-dev"],
    "cryptography": ["libffi-dev", "libssl-dev"],
    "psycopg2": ["libpq-dev"],
}


class ImportScanner(ast.NodeVisitor):
    def __init__(self, project_root_modules: Set[str]):
        self.imported_modules: Set[str] = set()
        self.project_root_modules = project_root_modules
        self.uses_match_case = False
        self.uses_type_union = False
        self.uses_walrus = False

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module and base_module not in self.project_root_modules:
                self.imported_modules.add(base_module)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.level == 0 and node.module:
            base_module = node.module.split(".")[0]
            if base_module and base_module not in self.project_root_modules:
                self.imported_modules.add(base_module)
        self.generic_visit(node)

    def visit_Match(self, node):
        self.uses_match_case = True
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        # Type union int | str (ast.BitOr)
        if isinstance(node.op, ast.BitOr):
            self.uses_type_union = True
        self.generic_visit(node)

    def visit_NamedExpr(self, node):
        self.uses_walrus = True
        self.generic_visit(node)


def parse_requirements_file(req_path: Path) -> List[str]:
    """Extracts package names from requirements.txt, normalizing them."""
    if not req_path.is_file():
        return []

    packages: List[str] = []
    try:
        content = req_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-r") or line.startswith("--"):
                continue
            # Strip version specifiers (e.g. aiogram>=3.4.1 -> aiogram)
            pkg_name = re.split(r"[><=~!]", line)[0].strip()
            if pkg_name:
                packages.append(pkg_name)
    except Exception:
        pass
    return packages


def resolve_dependencies(
    project_dir: Path,
    framework_hint: str = "generic"
) -> DependencyReport:
    """
    Scans project imports via AST, compares with requirements.txt, determines missing
    packages, maps to PyPI names, finds system apt libraries, and determines Python version.
    """
    py_files = sorted(list(project_dir.glob("*.py"))) + sorted(list(project_dir.rglob("*.py")))
    # Identify local project modules to prevent classifying local files as PyPI packages
    local_modules: Set[str] = {f.stem for f in py_files}
    for sub in project_dir.iterdir():
        if sub.is_dir() and (sub / "__init__.py").exists():
            local_modules.add(sub.name)

    scanner = ImportScanner(project_root_modules=local_modules)

    for py_file in py_files:
        try:
            code = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(code, filename=str(py_file))
            scanner.visit(tree)
        except Exception:
            continue

    # Filter out standard library
    external_imports = {m for m in scanner.imported_modules if m not in STDLIB_MODULES}

    # Map to PyPI packages
    pypi_needed: Set[str] = set()
    for imp in external_imports:
        mapped = IMPORT_TO_PYPI.get(imp, imp)
        pypi_needed.add(mapped)

    # Read existing requirements.txt
    req_file = project_dir / "requirements.txt"
    has_req = req_file.is_file()
    declared_pkgs = parse_requirements_file(req_file) if has_req else []

    # Case-insensitive comparison for missing packages
    declared_lower = {p.lower(): p for p in declared_pkgs}
    missing_pkgs: List[str] = []
    for pkg in sorted(list(pypi_needed)):
        if pkg.lower() not in declared_lower:
            missing_pkgs.append(pkg)

    # Determine system apt packages needed
    apt_packages: Set[str] = set()
    all_packages_set = {p.lower() for p in (declared_pkgs + missing_pkgs)}
    for pkg_key, apt_list in SYSTEM_APT_PACKAGES.items():
        if pkg_key.lower() in all_packages_set:
            apt_packages.update(apt_list)

    # Determine Python version
    reasons: List[str] = []
    detected_python_version = "3.12"  # default modern

    if framework_hint in ["aiogram_v2", "python_telegram_bot_v13"]:
        detected_python_version = "3.10"
        reasons.append(f"{framework_hint} eski kutubxonasi uchun Python 3.10 mosligi tanlandi.")
    elif scanner.uses_match_case:
        detected_python_version = "3.12"
        reasons.append("match/case sintaksisi aniqlandi (Python 3.10+ talab qilinadi).")
    else:
        reasons.append("Standart eng xavfsiz va tezkor Python 3.12-slim tanlandi.")

    # Generate recommended requirements.txt content
    recommended_lines: List[str] = []
    if has_req:
        try:
            existing_lines = req_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            recommended_lines.extend(existing_lines)
        except Exception:
            pass

    if missing_pkgs:
        recommended_lines.append("\n# BotHost Smart Analyzer tomonidan aniqlangan etishmayotgan paketlar:")
        for mp in missing_pkgs:
            recommended_lines.append(mp)

    recommended_requirements = "\n".join(recommended_lines).strip()

    return DependencyReport(
        has_requirements_file=has_req,
        declared_packages=declared_pkgs,
        ast_imported_packages=sorted(list(pypi_needed)),
        missing_packages=missing_pkgs,
        recommended_requirements=recommended_requirements,
        system_apt_packages=sorted(list(apt_packages)),
        detected_python_version=detected_python_version,
        reasons=reasons,
    )
