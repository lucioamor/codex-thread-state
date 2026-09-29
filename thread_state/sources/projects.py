from __future__ import annotations

from pathlib import PurePath
import re
from urllib.parse import urlparse


TAG = re.compile(r"^\[([^\]]+)\](?:\s+|$)")


def title_tag(title: str) -> str | None:
    match = TAG.match(title.strip())
    return match.group(1) if match else None


def without_title_tag(title: str) -> str:
    return TAG.sub("", title.strip()).strip()


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._").lower()
    return value[:32] or None


def project_tag(thread: dict, config: dict, current_base: str = "") -> str | None:
    existing = title_tag(current_base)
    if existing:
        return _clean(existing)
    cwd = str(thread.get("cwd") or "").replace("/", "\\").rstrip("\\")
    normalized = cwd.lower()
    mappings = sorted(config.get("projectRoots", {}).items(), key=lambda item: len(item[0]), reverse=True)
    for root, tag in mappings:
        if normalized.startswith(str(root).replace("/", "\\").lower().rstrip("\\")):
            return _clean(str(tag))
    origin = str((thread.get("gitInfo") or {}).get("originUrl") or "").rstrip("/")
    if origin:
        path = urlparse(origin).path if "://" in origin else origin.replace("\\", "/")
        slug = path.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
        if cleaned := _clean(slug):
            return cleaned
    if config.get("projects", {}).get("cwd_basename", True) and cwd:
        return _clean(PurePath(cwd.replace("\\", "/")).name)
    return None
