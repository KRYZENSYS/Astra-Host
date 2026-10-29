from pathlib import Path
from typing import Optional, List
from app.analyzer.models import AnalysisResult, SubProjectInfo
from app.analyzer.extractor import (
    validate_and_extract_safely,
    unwrap_single_folder,
    clean_junk,
    extract_env_variable_names,
    find_sub_projects,
)
from app.analyzer.framework_detector import detect_language, detect_telegram_framework
from app.analyzer.entry_detector import detect_entrypoints
from app.analyzer.dependency_resolver import resolve_dependencies
from app.analyzer.env_analyzer import analyze_environment_variables
from app.analyzer.dockerfile_generator import generate_optimized_dockerfile


def analyze_project(
    project_dir: str,
    zip_bytes: Optional[bytes] = None,
    user_entry_override: Optional[str] = None,
    sub_project_rel_path: Optional[str] = None
) -> AnalysisResult:
    """
    Main entrypoint for BotHost Smart Analyzer.
    Analyzes project statically, safely, and deterministically without executing untrusted code.
    """
    work_dir = Path(project_dir).resolve()
    junk_cleaned: List[str] = []
    known_env_names: List[str] = []

    # 1. Extraction if zip_bytes provided
    if zip_bytes:
        extracted_root, junk_cleaned, known_env_names = validate_and_extract_safely(
            zip_bytes=zip_bytes,
            target_extract_dir=str(work_dir)
        )
        work_dir = Path(extracted_root).resolve()
    else:
        # Working with pre-extracted or local directory
        work_dir = unwrap_single_folder(work_dir)
        known_env_names = extract_env_variable_names(work_dir)
        junk_cleaned = clean_junk(work_dir)

    # If user selected a specific sub-project
    if sub_project_rel_path:
        target_sub = (work_dir / sub_project_rel_path).resolve()
        if target_sub.is_dir() and str(target_sub).startswith(str(work_dir)):
            work_dir = target_sub

    # 2. Check language
    lang, is_supported, lang_warning = detect_language(work_dir)
    if not is_supported:
        return AnalysisResult(
            is_supported_language=False,
            detected_language=lang,
            language_warning=lang_warning,
            project_root=str(work_dir),
            junk_files_cleaned=junk_cleaned,
            confidence_score=0,
            confidence_level="low",
            warnings=[lang_warning or "Qo'llab-quvvatlanmaydigan dasturlash tili."],
        )

    # 3. Detect sub-projects
    sub_dirs = find_sub_projects(work_dir)
    sub_projects_info: List[SubProjectInfo] = []
    for sub in sub_dirs:
        sub_fw, sub_disp, _ = detect_telegram_framework(sub)
        sub_entry, _ = detect_entrypoints(sub)
        sub_projects_info.append(SubProjectInfo(
            relative_path=str(sub.relative_to(work_dir)),
            name=sub.name,
            entrypoint=sub_entry,
            telegram_framework=sub_disp,
            confidence=85 if sub_fw != "generic" else 50,
        ))

    # 4. Telegram Framework detection
    fw_key, fw_display, secondary_roles = detect_telegram_framework(work_dir)

    # 5. Scored entrypoint detection
    recommended_entry, candidates = detect_entrypoints(work_dir, user_override=user_entry_override)

    # 6. Dependency resolution & Python version
    dep_report = resolve_dependencies(work_dir, framework_hint=fw_key)

    # 7. Environment variable discovery
    env_defs, sqlite_warning = analyze_environment_variables(work_dir, known_env_names)

    # 8. Generate Dockerfile
    dockerfile_content = generate_optimized_dockerfile(
        entrypoint=recommended_entry,
        python_version=dep_report.detected_python_version,
        apt_packages=dep_report.system_apt_packages
    )

    # Write Dockerfile and updated requirements.txt to disk
    try:
        (work_dir / "Dockerfile").write_text(dockerfile_content, encoding="utf-8")
        if dep_report.recommended_requirements:
            (work_dir / "requirements.txt").write_text(dep_report.recommended_requirements, encoding="utf-8")
    except Exception:
        pass

    # 9. Calculate confidence score
    confidence_score = 50  # base
    warnings: List[str] = []

    # Framework signal
    if fw_key != "generic":
        confidence_score += 20
    else:
        warnings.append("Maxsus Telegram karkasi (aiogram/telebot/va hk) aniqlanmadi, umumiy Python rejimida ishlatiladi.")

    # Entrypoint quality
    top_candidate = next((c for c in candidates if c.filename == recommended_entry), None)
    if top_candidate:
        if top_candidate.has_polling:
            confidence_score += 15
        if top_candidate.has_main_block:
            confidence_score += 10
        if top_candidate.score < 20:
            confidence_score -= 20
            warnings.append(f"{recommended_entry} faylida botni ishga tushiruvchi aniq funksiyalar kamroq aniqlandi.")

    # Requirements presence
    if dep_report.has_requirements_file:
        confidence_score += 5
    elif dep_report.missing_packages:
        warnings.append(f"requirements.txt topilmadi. {len(dep_report.missing_packages)} ta etishmayotgan paket avtomatik aniqlandi va qo'shildi.")

    # Sub-projects note
    if len(sub_projects_info) > 1 and not sub_project_rel_path:
        warnings.append(f"Arxiv ichida bir nechta mustaqil loyihalar ({len(sub_projects_info)} ta) aniqlandi. Kerakli loyihani tanlashingiz mumkin.")

    # SQLite warning
    if sqlite_warning:
        warnings.append(sqlite_warning)

    # Bound confidence score
    confidence_score = max(10, min(100, confidence_score))
    if confidence_score >= 85:
        confidence_level = "high"
    elif confidence_score >= 60:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    return AnalysisResult(
        is_supported_language=True,
        detected_language="python",
        language_warning=None,
        project_root=str(work_dir),
        sub_projects=sub_projects_info,
        selected_sub_project=sub_project_rel_path,
        junk_files_cleaned=junk_cleaned,
        framework=fw_key,
        framework_display_name=fw_display,
        secondary_roles=secondary_roles,
        recommended_entrypoint=recommended_entry,
        entrypoint_candidates=candidates,
        dependencies=dep_report,
        env_vars=env_defs,
        sqlite_warning=sqlite_warning,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        warnings=warnings,
        dockerfile_content=dockerfile_content,
    )
