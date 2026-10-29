import ast
import hashlib
import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from app.analyzer.models import EntryCandidate

STANDARD_NAMES = {"main.py", "bot.py", "app.py", "run.py", "start.py"}

def get_file_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of file content to identify exact duplicate files."""
    try:
        data = file_path.read_bytes()
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return ""

class EntrypointVisitor(ast.NodeVisitor):
    def __init__(self):
        self.has_main_block = False
        self.has_polling = False
        self.has_async_run = False
        self.total_defs = 0
        self.total_statements = 0

    def visit_If(self, node: ast.If):
        # Check `if __name__ == '__main__':`
        try:
            test = node.test
            if isinstance(test, ast.Compare):
                left = test.left
                if isinstance(left, ast.Name) and left.id == "__name__":
                    for comparator in test.comparators:
                        if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
                            self.has_main_block = True
                        elif isinstance(comparator, ast.Str) and comparator.s == "__main__":
                            self.has_main_block = True
        except Exception:
            pass
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        self.total_statements += 1
        try:
            # Check asyncio.run(...)
            if isinstance(node.func, ast.Attribute):
                attr_name = node.func.attr
                if attr_name in ["run", "run_until_complete"]:
                    if isinstance(node.func.value, ast.Name) and node.func.value.id in ["asyncio", "loop"]:
                        self.has_async_run = True

                # Check polling calls
                if attr_name in [
                    "start_polling", "infinity_polling", "run_polling",
                    "start_webhook", "polling", "run"
                ]:
                    self.has_polling = True
            elif isinstance(node.func, ast.Name):
                if node.func.id in ["start_polling", "run_bot", "main"]:
                    self.has_polling = True
        except Exception:
            pass
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.total_defs += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.total_defs += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.total_defs += 1
        self.generic_visit(node)


def check_dockerfile_or_procfile_hints(project_dir: Path) -> Optional[str]:
    """Inspects existing Dockerfile or Procfile if present for CMD/ENTRYPOINT hint."""
    df = project_dir / "Dockerfile"
    if df.is_file():
        try:
            text = df.read_text(encoding="utf-8", errors="ignore")
            # Look for CMD ["python", "xyz.py"] or ENTRYPOINT
            m = re.search(r'(?:CMD|ENTRYPOINT)\s*\[?.*["\']([a-zA-Z0-9_\-\./]+\.py)["\']', text)
            if m:
                return Path(m.group(1)).name
        except Exception:
            pass

    proc = project_dir / "Procfile"
    if proc.is_file():
        try:
            text = proc.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'python\s+([a-zA-Z0-9_\-\./]+\.py)', text)
            if m:
                return Path(m.group(1)).name
        except Exception:
            pass

    return None


def detect_entrypoints(project_dir: Path, user_override: Optional[str] = None) -> Tuple[str, List[EntryCandidate]]:
    """
    Scans all Python files and ranks them by execution likelihood.
    Returns: (recommended_entrypoint, sorted_candidates)
    """
    py_files = sorted(list(project_dir.glob("*.py")))
    if not py_files:
        py_files = sorted(list(project_dir.rglob("*.py")))

    if not py_files:
        default_candidate = EntryCandidate(
            filename="main.py",
            score=0,
            reasons=["Python fayllari topilmadi, standart main.py tavsiya etildi."]
        )
        return ("main.py", [default_candidate])

    dockerfile_hint = check_dockerfile_or_procfile_hints(project_dir)

    candidates: List[EntryCandidate] = []
    seen_hashes: Dict[str, str] = {}  # sha256 -> first_filename

    for py_file in py_files:
        rel_name = py_file.name
        sha = get_file_sha256(py_file)
        reasons: List[str] = []
        score = 0

        # Check duplicate
        is_dup_of = None
        if sha and sha in seen_hashes:
            is_dup_of = seen_hashes[sha]
            reasons.append(f"Ushbu fayl {is_dup_of} faylining nusxasi (SHA256 mos).")
            score -= 50
        else:
            if sha:
                seen_hashes[sha] = rel_name

        try:
            code_text = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(code_text, filename=str(py_file))
        except Exception:
            # Syntax error or unparseable file
            candidates.append(EntryCandidate(
                filename=rel_name,
                score=-50,
                reasons=["Faylda sintaktik xatolik mavjud yoki uni tahlil qilib bo'lmadi."],
                sha256=sha,
                is_duplicate_of=is_dup_of,
            ))
            continue

        visitor = EntrypointVisitor()
        visitor.visit(tree)

        # 1. Main block (+30)
        if visitor.has_main_block or ("if __name__" in code_text and "__main__" in code_text):
            score += 30
            reasons.append("__main__ bloki mavjud (+30)")

        # 2. Polling call (+40)
        if visitor.has_polling or any(p in code_text for p in ["start_polling", "infinity_polling", "run_polling"]):
            score += 40
            reasons.append("Telegram botni ishga tushirish (polling) funksiyasi chaqirilgan (+40)")

        # 3. Asyncio.run (+20)
        if visitor.has_async_run or "asyncio.run(" in code_text:
            score += 20
            reasons.append("asyncio.run() asinxron hodisalar sikli mavjud (+20)")

        # 4. Standard name (+15)
        if rel_name.lower() in STANDARD_NAMES:
            score += 15
            reasons.append(f"Standart boshlang'ich fayl nomi ({rel_name}) (+15)")

        # 5. Dockerfile hint (+25)
        if dockerfile_hint and dockerfile_hint.lower() == rel_name.lower():
            score += 25
            reasons.append("Mavjud Dockerfile yoki Procfile ko'rsatmasiga mos (+25)")

        # Negative factors
        # File only defining functions/classes and no executable statements at top level
        if visitor.total_defs > 3 and not visitor.has_main_block and not visitor.has_polling:
            score -= 20
            reasons.append("Fayl asosan sinf va funksiyalar kutubxonasiga o'xshaydi (-20)")

        if rel_name.startswith("patch_") or rel_name.startswith("test_") or "helper" in rel_name:
            score -= 25
            reasons.append("Yordamchi yoki sinov fayli belgisi (-25)")

        candidates.append(EntryCandidate(
            filename=rel_name,
            score=score,
            reasons=reasons,
            has_main_block=visitor.has_main_block,
            has_polling=visitor.has_polling,
            has_async_run=visitor.has_async_run,
            is_duplicate_of=is_dup_of,
            sha256=sha,
        ))

    # Sort candidates by score descending
    candidates.sort(key=lambda c: c.score, reverse=True)

    # Handle user override if requested
    if user_override and user_override.strip():
        override_clean = user_override.strip()
        for c in candidates:
            if c.filename == override_clean:
                return (override_clean, candidates)
        if (project_dir / override_clean).is_file():
            candidates.insert(0, EntryCandidate(
                filename=override_clean,
                score=100,
                reasons=["Foydalanuvchi tomonidan tanlangan kirish fayli"]
            ))
            return (override_clean, candidates)

    recommended = candidates[0].filename if candidates else "main.py"
    return (recommended, candidates)
