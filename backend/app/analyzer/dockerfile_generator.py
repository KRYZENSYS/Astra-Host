from typing import List

def generate_optimized_dockerfile(
    entrypoint: str,
    python_version: str = "3.12",
    apt_packages: List[str] = None
) -> str:
    """
    Renders production-grade multi-stage Dockerfile with non-root UID 10001,
    /data volume setup, apt package installation, and unbuffered logging.
    """
    if apt_packages is None:
        apt_packages = []

    apt_install_block = ""
    if apt_packages:
        pkgs_joined = " \\\n        ".join(apt_packages)
        apt_install_block = f"""# Install required system packages
RUN apt-get update && \\
    apt-get install -y --no-install-recommends \\
        {pkgs_joined} && \\
    rm -rf /var/lib/apt/lists/*
"""

    dockerfile = f"""# ==========================================
# BotHost Hardened Container for Telegram Bot
# Base: python:{python_version}-slim
# ==========================================
FROM python:{python_version}-slim AS runner

# Optimize Python execution in Docker
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    DATA_DIR=/data \\
    HOME=/tmp

WORKDIR /app

{apt_install_block}
# Create unprivileged botuser (UID 10001) and prepare /data mount point
RUN useradd -u 10001 -m -s /bin/bash botuser && \\
    mkdir -p /data /app && \\
    chown -R botuser:botuser /data /app /tmp

# Copy requirements and install dependencies
COPY requirements.txt* ./
RUN if [ -f requirements.txt ] && [ -s requirements.txt ]; then \\
        pip install --no-cache-dir -r requirements.txt; \\
    fi

# Copy bot source code with proper ownership
COPY --chown=botuser:botuser . .

# Run strictly as unprivileged user
USER 10001:10001

CMD ["python", "{entrypoint}"]
"""
    return dockerfile
