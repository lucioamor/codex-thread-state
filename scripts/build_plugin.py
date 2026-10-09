"""Build a public plugin archive from an explicit allowlist, without dependencies."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ["plugin.json", ".agents/plugins/marketplace.json", "thread_state.py", "README.md", "LICENSE", "NOTICE",
         "CHANGELOG.md", "docs/plugin-installation.md"]
DIRS = ["thread_state", "skills", "hooks"]


def build(destination=None):
    import json
    version = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))["version"]
    output = Path(destination) if destination else ROOT / "dist" / f"thread-state-{version}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = [ROOT / name for name in FILES]
    for folder in DIRS:
        paths.extend(p for p in (ROOT / folder).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts
                     and p.suffix not in {".pyc", ".pyo"})
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, "thread-state/" + path.relative_to(ROOT).as_posix())
    return output


if __name__ == "__main__":
    print(build())
