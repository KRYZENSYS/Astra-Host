import re
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from app.analyzer.dependency_resolver import IMPORT_TO_PYPI, SYSTEM_APT_PACKAGES
from app.analyzer.dockerfile_generator import generate_optimized_dockerfile

APT_SO_MAPPINGS: Dict[str, str] = {
    "libgl.so": "libgl1",
    "libglib-2.0.so": "libglib2.0-0",
    "libgthread-2.0.so": "libglib2.0-0",
    "libsm.so": "libsm6",
    "libxext.so": "libxext6",
    "libxrender.so": "libxrender1",
    "libjpeg.so": "libjpeg-dev",
    "libz.so": "zlib1g-dev",
    "libfreetype.so": "libfreetype6-dev",
    "libmupdf.so": "libmupdf-dev",
    "libpq.so": "libpq-dev",
    "libxml2.so": "libxml2-dev",
    "libxslt.so": "libxslt1-dev",
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffmpeg",
}

class AutoFixAction:
    def __init__(self, action_type: str, description: str, fixed: bool, detail: Optional[str] = None):
        self.action_type = action_type  # "pip_install", "apt_install", "missing_env", "python_version", "permission"
        self.description = description
        self.fixed = fixed
        self.detail = detail

    def to_dict(self):
        return {
            "action_type": self.action_type,
            "description": self.description,
            "fixed": self.fixed,
            "detail": self.detail
        }


def analyze_failure_and_autofix(
    project_dir: Path,
    error_logs: str,
    current_attempt: int = 1,
    current_python_version: str = "3.12",
    entrypoint: str = "main.py"
) -> Tuple[bool, Optional[AutoFixAction]]:
    """
    Analyzes container startup or build error logs and automatically patches configuration.
    Returns: (can_retry_build, auto_fix_action)
    """
    if current_attempt > 3:
        return False, AutoFixAction("max_attempts", "Maksimal avtomatik tuzatish chegarasiga (3 marta) yetildi.", False)

    req_file = project_dir / "requirements.txt"
    dockerfile = project_dir / "Dockerfile"

    # 1. Check ModuleNotFoundError: No module named 'xyz'
    m_mod = re.search(r"ModuleNotFoundError:\s+No module named\s+['\"]([^'\"]+)['\"]", error_logs)
    if m_mod:
        missing_module = m_mod.group(1).split(".")[0]
        pypi_pkg = IMPORT_TO_PYPI.get(missing_module, missing_module)

        # Append to requirements.txt
        existing_reqs = req_file.read_text(encoding="utf-8", errors="ignore") if req_file.exists() else ""
        if pypi_pkg.lower() not in existing_reqs.lower():
            new_reqs = existing_reqs.strip() + f"\n{pypi_pkg}\n"
            req_file.write_text(new_reqs, encoding="utf-8")
            action = AutoFixAction(
                action_type="pip_install",
                description=f"Etishmayotgan '{missing_module}' moduli aniqlandi va '{pypi_pkg}' paket sifatida requirements.txt ga qo'shildi.",
                fixed=True,
                detail=pypi_pkg
            )
            return True, action

    # 2. Check Shared Object Library error: lib*.so.* cannot open shared object file
    m_so = re.search(r"(?:error while loading shared libraries|ImportError):\s+([^:]+\.so[^\s:]*)", error_logs)
    if m_so:
        missing_lib = m_so.group(1).strip()
        matched_apt = None
        for so_prefix, apt_pkg in APT_SO_MAPPINGS.items():
            if so_prefix in missing_lib.lower():
                matched_apt = apt_pkg
                break

        if not matched_apt:
            matched_apt = "libglib2.0-0"  # common fallback for C-extensions

        # Re-generate Dockerfile with new apt package
        new_df = generate_optimized_dockerfile(
            entrypoint=entrypoint,
            python_version=current_python_version,
            apt_packages=[matched_apt, "libgl1"]
        )
        dockerfile.write_text(new_df, encoding="utf-8")
        action = AutoFixAction(
            action_type="apt_install",
            description=f"Tizim darajasidagi '{missing_lib}' kutubxonasi aniqlandi va '{matched_apt}' tizim paketi o'rnatildi.",
            fixed=True,
            detail=matched_apt
        )
        return True, action

    # 3. Check KeyError: 'VARIABLE_NAME'
    m_key = re.search(r"KeyError:\s+['\"]([^'\"]+)['\"]", error_logs)
    if m_key:
        var_name = m_key.group(1).strip()
        action = AutoFixAction(
            action_type="missing_env",
            description=f"Dastur kodi '{var_name}' muhit o'zgaruvchisini talab qilmoqda (KeyError).",
            fixed=False,
            detail=var_name
        )
        return False, action

    # 4. Check Permission denied write errors (e.g. SQLite writing to read-only root)
    if "PermissionError: [Errno 13] Permission denied" in error_logs:
        action = AutoFixAction(
            action_type="permission",
            description="Konteyner ildiz fayl tizimi read-only himoyalangan. Bot /data papkasiga yo'naltirilmoqda.",
            fixed=True,
            detail="/data"
        )
        return True, action

    # 5. Check Python version / SyntaxError on older syntax
    if "SyntaxError" in error_logs and current_python_version == "3.10":
        new_df = generate_optimized_dockerfile(
            entrypoint=entrypoint,
            python_version="3.12"
        )
        dockerfile.write_text(new_df, encoding="utf-8")
        action = AutoFixAction(
            action_type="python_version",
            description="Sintaktik xatolik sababli Python 3.12 talqini tanlandi.",
            fixed=True,
            detail="3.12"
        )
        return True, action

    return False, None
