from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

@dataclass
class EntryCandidate:
    filename: str
    score: int
    reasons: List[str]
    has_main_block: bool = False
    has_polling: bool = False
    has_async_run: bool = False
    is_duplicate_of: Optional[str] = None
    sha256: str = ""

@dataclass
class EnvVarDefinition:
    name: str
    is_required: bool
    var_type: str  # "telegram_token", "secret_key", "path", "url", "number", "string"
    description: str
    default_value: Optional[str] = None
    source_locations: List[str] = field(default_factory=list)
    suggested_value: Optional[str] = None
    validation_regex: Optional[str] = None

@dataclass
class DependencyReport:
    has_requirements_file: bool
    declared_packages: List[str]
    ast_imported_packages: List[str]
    missing_packages: List[str]
    recommended_requirements: str
    system_apt_packages: List[str]
    detected_python_version: str  # e.g. "3.12" or "3.10"
    reasons: List[str] = field(default_factory=list)

@dataclass
class SubProjectInfo:
    relative_path: str
    name: str
    entrypoint: str
    telegram_framework: str
    confidence: int

@dataclass
class AnalysisResult:
    is_supported_language: bool
    detected_language: str  # "python" or "nodejs" or "unknown"
    language_warning: Optional[str] = None
    
    # Root & Sub-projects
    project_root: str = "."
    sub_projects: List[SubProjectInfo] = field(default_factory=list)
    selected_sub_project: Optional[str] = None
    junk_files_cleaned: List[str] = field(default_factory=list)
    
    # Framework
    framework: str = "unknown"  # "aiogram_v3", "aiogram_v2", "python_telegram_bot_v20", "python_telegram_bot_v13", "telebot", "pyrogram", "telethon", "generic"
    framework_display_name: str = "Noma'lum karkas"
    secondary_roles: List[str] = field(default_factory=list)  # "web_server", "webapp", "scheduler", "userbot"
    
    # Entrypoint
    recommended_entrypoint: str = "main.py"
    entrypoint_candidates: List[EntryCandidate] = field(default_factory=list)
    
    # Dependencies
    dependencies: Optional[DependencyReport] = None
    
    # Environment Variables
    env_vars: List[EnvVarDefinition] = field(default_factory=list)
    sqlite_warning: Optional[str] = None
    
    # Overall score & confidence
    confidence_score: int = 0  # 0 to 100
    confidence_level: str = "medium"  # "high", "medium", "low"
    warnings: List[str] = field(default_factory=list)
    dockerfile_content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
