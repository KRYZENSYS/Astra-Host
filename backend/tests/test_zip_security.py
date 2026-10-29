import io
import os
import zipfile
import pytest
from pathlib import Path
from fastapi import HTTPException
from app.services.zip_service import validate_and_extract_bot_zip, is_junk_path


def create_mock_zip(file_dict: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in file_dict.items():
            zf.writestr(filename, content)
    return buffer.getvalue()


def test_zip_slip_relative_path_blocked(tmp_path):
    # Archive attempting to escape target directory using ../
    malicious_zip = create_mock_zip({
        "../../evil.py": b"print('hacked')",
        "main.py": b"print('ok')",
    })

    with pytest.raises(HTTPException) as exc_info:
        validate_and_extract_bot_zip(malicious_zip, str(tmp_path))

    assert exc_info.value.status_code == 400
    assert "xavfli yo'l aniqlandi" in exc_info.value.detail or "Zip-slip" in exc_info.value.detail


def test_zip_slip_absolute_path_blocked(tmp_path):
    # Archive with absolute path starting with /
    malicious_zip = create_mock_zip({
        "/root/.bashrc": b"export PWNED=1",
        "bot.py": b"print('bot')",
    })

    with pytest.raises(HTTPException) as exc_info:
        validate_and_extract_bot_zip(malicious_zip, str(tmp_path))

    assert exc_info.value.status_code == 400
    assert "Xavfsizlik xatosi" in exc_info.value.detail


def test_junk_files_and_directories_ignored(tmp_path):
    # Archive with development junk that should not enter container
    zip_with_junk = create_mock_zip({
        "main.py": b"print('legit bot')",
        "requirements.txt": b"aiogram==3.18.0\n",
        "__pycache__/cache.pyc": b"\x00\x00\x00",
        ".git/config": b"[core]\nrepositoryformatversion = 0",
        ".env": b"BOT_TOKEN=leak_this_token",
        "secrets.db": b"sqlite database bytes",
        "debug.log": b"log lines",
        "backups/archive.zip": b"old backup",
    })

    extracted = validate_and_extract_bot_zip(zip_with_junk, str(tmp_path))

    # Only legit files extracted
    assert set(extracted) == {"main.py", "requirements.txt"}
    assert (tmp_path / "main.py").is_file()
    assert (tmp_path / "requirements.txt").is_file()

    # Verify junk was NOT written to disk
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / ".git").exists()
    assert not (tmp_path / "__pycache__").exists()
    assert not (tmp_path / "secrets.db").exists()
    assert not (tmp_path / "debug.log").exists()
    assert not (tmp_path / "backups").exists()


def test_single_top_level_wrapper_flattened(tmp_path):
    # GitHub / archive tool creates single folder: my-bot-main/main.py
    nested_zip = create_mock_zip({
        "telegram-bot-master/main.py": b"print('flattened')",
        "telegram-bot-master/config.py": b"PORT = 8080",
        "telegram-bot-master/requirements.txt": b"aiogram==3.18.0\n",
    })

    extracted = validate_and_extract_bot_zip(nested_zip, str(tmp_path))

    # Top-level directory prefix is stripped
    assert "main.py" in extracted
    assert "config.py" in extracted
    assert "requirements.txt" in extracted
    assert (tmp_path / "main.py").is_file()
    assert (tmp_path / "config.py").is_file()
