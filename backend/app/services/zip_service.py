import os
import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from fastapi import HTTPException, status
from app.config import settings

# Junk paths and patterns to strictly ignore during extraction
JUNK_DIRS = {"__pycache__", ".git", "backups"}
JUNK_EXTENSIONS = {".pyc", ".db", ".log"}
JUNK_FILENAMES = {".env"}


def is_junk_path(relative_path: str) -> bool:
    """Checks if file or folder is junk that must never be copied into container."""
    parts = Path(relative_path).parts
    # Check directory names
    for p in parts:
        if p in JUNK_DIRS:
            return True
    # Check filename
    filename = Path(relative_path).name
    if filename in JUNK_FILENAMES:
        return True
    # Check extension
    _, ext = os.path.splitext(filename.lower())
    if ext in JUNK_EXTENSIONS:
        return True
    return False


def validate_and_extract_bot_zip(zip_bytes: bytes, destination_dir: str) -> list[str]:
    """
    Validates and safely extracts a bot source zip archive:
    - Max 20 MB zip size
    - Max 100 MB uncompressed size (zip-bomb protection)
    - Max 2000 files
    - Zip-Slip protection (reject traversal and absolute paths)
    - Rejects symlinks
    - Flattens single top-level directory if present
    - Ignores junk (__pycache__, .git, *.pyc, .env, *.db, *.log, backups/)
    Returns: list of extracted relative filenames
    """
    if len(zip_bytes) > settings.MAX_ZIP_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arxiv hajmi ruxsat etilgan limitdan ({settings.MAX_ZIP_SIZE_BYTES // (1024*1024)} MB) katta.",
        )

    try:
        archive = zipfile.ZipFile(BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fayl to'g'ri ZIP formatida emas.")

    members = archive.infolist()

    # 1. File count check
    if len(members) > settings.MAX_ARCHIVE_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arxiv ichidagi fayllar soni limitdan ({settings.MAX_ARCHIVE_FILES}) oshib ketdi.",
        )

    # 2. Uncompressed size and symlink checks
    total_uncompressed = 0
    clean_members: list[zipfile.ZipInfo] = []

    for m in members:
        # Check for symlink
        # In zip format, symlinks have Unix file attributes with S_IFLNK (0o120000)
        mode = m.external_attr >> 16
        if mode and (mode & 0o170000) == 0o120000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Xavfsizlik xatosi: Arxivda symlink (ramziy havola) aniqlandi ({m.filename}).",
            )

        # Zip-bomb protection
        total_uncompressed += m.file_size
        if total_uncompressed > settings.MAX_UNCOMPRESSED_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arxiv ochilgandagi hajmi limitdan ({settings.MAX_UNCOMPRESSED_BYTES // (1024*1024)} MB) oshib ketdi.",
            )

        # Zip-Slip protection
        name = m.filename.replace("\\", "/")
        if name.startswith("/") or name.startswith("../") or "/../" in name or name.endswith("/.."):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Xavfsizlik xatosi: Arxivda xavfli yo'l aniqlandi ({m.filename}).",
            )

        # Filter out junk
        if not is_junk_path(name):
            clean_members.append(m)

    if not clean_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arxivda yaroqli fayllar topilmadi.",
        )

    # 3. Detect single top-level folder and flatten
    # If all members have the same root directory prefix, we strip it
    top_level_dirs = set()
    for m in clean_members:
        parts = Path(m.filename.replace("\\", "/")).parts
        if parts:
            top_level_dirs.add(parts[0])

    prefix_to_strip = ""
    if len(top_level_dirs) == 1:
        single_dir = list(top_level_dirs)[0]
        # Verify it's a directory wrapper
        is_wrapper = any(len(Path(m.filename.replace("\\", "/")).parts) > 1 for m in clean_members)
        if is_wrapper:
            prefix_to_strip = single_dir + "/"

    # 4. Extract into clean destination directory
    dest_path = Path(destination_dir).resolve()
    shutil.rmtree(dest_path, ignore_errors=True)
    dest_path.mkdir(parents=True, exist_ok=True)

    extracted_files: list[str] = []

    for m in clean_members:
        orig_name = m.filename.replace("\\", "/")
        if prefix_to_strip and orig_name.startswith(prefix_to_strip):
            rel_name = orig_name[len(prefix_to_strip):]
        else:
            rel_name = orig_name

        if not rel_name or rel_name.endswith("/"):
            continue

        target_file_path = (dest_path / rel_name).resolve()

        # Final traversal guard
        if dest_path not in target_file_path.parents and target_file_path != dest_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Xavfsizlik xatosi: Zip-slip cheklovi buzildi.",
            )

        target_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file contents safely
        with archive.open(m) as source, open(target_file_path, "wb") as target:
            shutil.copyfileobj(source, target)

        extracted_files.append(rel_name)

    return extracted_files


# Backward compatibility alias
validate_and_extract_zip = validate_and_extract_bot_zip
