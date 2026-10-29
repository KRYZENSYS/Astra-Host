import os
from pathlib import Path

STANDARD_ENTRYPOINTS = ["main.py", "bot.py", "app.py", "run.py", "start.py"]


def scan_file_for_main_block(file_path: Path) -> bool:
    """Checks if a python file contains an `if __name__ == '__main__'` block."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        # Normalize quotes and spacing
        return ('__name__' in content and '__main__' in content and 'if ' in content)
    except Exception:
        return False


def detect_or_verify_entrypoint(source_dir: str, user_override: str | None = None) -> tuple[str, bool]:
    """
    Detects entry file:
    1. If user provided a non-empty override and the file exists, use it.
    2. Check standard names (main.py, bot.py, app.py).
    3. Look for the first python file containing `if __name__ == '__main__'`.
    4. Fallback to any .py file, else 'main.py'.
    Returns: (entrypoint_filename, requirements_present_bool)
    """
    src_path = Path(source_dir)

    # Requirements.txt check
    reqs_path = src_path / "requirements.txt"
    has_requirements = reqs_path.is_file()
    if not has_requirements:
        # Create empty requirements.txt as required
        reqs_path.write_text("# Auto-generated empty requirements.txt\n", encoding="utf-8")

    # Entrypoint resolution
    if user_override and user_override.strip():
        override_clean = user_override.strip()
        if (src_path / override_clean).is_file():
            return override_clean, has_requirements

    # Standard names check
    for std_name in STANDARD_ENTRYPOINTS:
        candidate = src_path / std_name
        if candidate.is_file() and scan_file_for_main_block(candidate):
            return std_name, has_requirements

    for std_name in STANDARD_ENTRYPOINTS:
        if (src_path / std_name).is_file():
            return std_name, has_requirements

    # Scan all .py files for __main__ block
    py_files = sorted(list(src_path.glob("*.py")))
    for py_file in py_files:
        if scan_file_for_main_block(py_file):
            return py_file.name, has_requirements

    if py_files:
        return py_files[0].name, has_requirements

    return "main.py", has_requirements


def generate_dockerfile(source_dir: str, entrypoint: str):
    """
    Renders hardened Dockerfile based on python:3.12-slim:
    - non-root user `botuser` (UID 10001)
    - install requirements with `--no-cache-dir`
    - copy source with ownership
    - CMD ["python", "<entrypoint>"]
    """
    src_path = Path(source_dir)
    dockerfile_path = src_path / "Dockerfile"

    dockerfile_content = f"""FROM python:3.12-slim

# Prevent bytecode writing and ensure unbuffered stdout/stderr logging
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    DATA_DIR=/data

WORKDIR /app

# Create unprivileged botuser (UID 10001) and /data mount point
RUN useradd -u 10001 -m botuser && \\
    mkdir -p /data && \\
    chown -R botuser:botuser /data /app

# Install dependencies if requirements.txt exists
COPY requirements.txt* ./
RUN if [ -f requirements.txt ] && [ -s requirements.txt ]; then \\
        pip install --no-cache-dir -r requirements.txt; \\
    fi

# Copy bot source code with proper non-root permissions
COPY --chown=botuser:botuser . .

# Run as non-root
USER 10001:10001

CMD ["python", "{entrypoint}"]
"""
    dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
