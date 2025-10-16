"""Utility to copy the latest weekly PDF report to the user's Downloads folder
and open File Explorer so the user can download/open it. No server required.

Usage:
  python download_report.py

Behavior:
  - Finds newest PDF in logs/reports
  - Copies it to ~/Downloads with a friendly prefix
  - Opens Explorer and selects the copied file on Windows
"""
from pathlib import Path
import shutil
import sys
import platform


def find_latest_report(reports_dir: Path) -> Path | None:
    # Check the given path first
    candidates = []
    candidates.append(reports_dir)

    # Also check upward from the repo root (parent and grandparent)
    repo_root = Path(__file__).parent
    parent = repo_root.parent
    grandparent = parent.parent
    candidates.append(parent / 'logs' / 'reports')
    candidates.append(grandparent / 'logs' / 'reports')

    # Also check sibling 'logs/reports' at the workspace root if present
    workspace_logs = repo_root.parent.parent / 'logs' / 'reports'
    candidates.append(workspace_logs)

    seen = set()
    for d in candidates:
        try:
            if not d:
                continue
            d = d.resolve()
            if str(d) in seen:
                continue
            seen.add(str(d))
            if d.exists() and d.is_dir():
                pdfs = sorted([p for p in d.glob('*.pdf')], key=lambda p: p.stat().st_mtime, reverse=True)
                if pdfs:
                    return pdfs[0]
        except Exception:
            continue

    # Final fallback: search upwards from repo_root until filesystem root for logs/reports
    cur = repo_root
    for _ in range(6):
        candidate = cur / 'logs' / 'reports'
        if candidate.exists() and candidate.is_dir():
            pdfs = sorted([p for p in candidate.glob('*.pdf')], key=lambda p: p.stat().st_mtime, reverse=True)
            if pdfs:
                return pdfs[0]
        if cur.parent == cur:
            break
        cur = cur.parent

    return None


def copy_to_downloads(src: Path) -> Path:
    home = Path.home()
    downloads = home / 'Downloads'
    downloads.mkdir(parents=True, exist_ok=True)

    dest_name = f"ActivityMonitor-{src.name}"
    dest = downloads / dest_name
    # If file exists, append timestamp
    if dest.exists():
        import time
        dest = downloads / f"ActivityMonitor-{int(time.time())}-{src.name}"

    shutil.copy2(src, dest)
    return dest


def reveal_in_explorer(path: Path) -> None:
    try:
        if platform.system() == 'Windows':
            # explorer accepts "/select,PATH"
            import subprocess
            subprocess.run(["explorer", "/select," + str(path)])
        elif platform.system() == 'Darwin':
            import subprocess
            subprocess.run(["open", "-R", str(path)])
        else:
            # On Linux, open the folder
            import subprocess
            subprocess.run(["xdg-open", str(path.parent)])
    except Exception:
        pass


def main() -> int:
    repo_root = Path(__file__).parent
    reports_dir = repo_root / 'logs' / 'reports'

    latest = find_latest_report(reports_dir)
    if not latest:
        print("No PDF reports found in:", reports_dir)
        return 2

    dest = copy_to_downloads(latest)
    print(f"Copied latest report to: {dest}")
    reveal_in_explorer(dest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
