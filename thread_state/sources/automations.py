from pathlib import Path


def is_recurring(thread_id: str, automations_root: Path) -> bool:
    if not automations_root.exists(): return False
    return any(thread_id in path.read_text(encoding="utf-8", errors="replace")
               for path in automations_root.glob("*/automation.toml"))
