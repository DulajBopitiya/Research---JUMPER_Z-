"""
scripts/install_hooks.py

Installs project Git hooks from scripts/hooks/ into .git/hooks/.
Run once after cloning the repository, or after adding new hooks.

Usage:
    python scripts/install_hooks.py

What it does:
    1. Finds the .git/hooks/ directory
    2. Copies every file from scripts/hooks/ into it
    3. Sets executable permissions on each hook (required on Unix)
    4. Reports the result clearly

Safe to re-run — existing hooks are overwritten with the latest version.
"""

from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path


# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------

# Source: hooks live here in version control
HOOKS_SOURCE_DIR = Path(__file__).resolve().parent / "hooks"

# Destination: Git reads hooks from here
HOOKS_DEST_DIR   = Path(__file__).resolve().parents[1] / ".git" / "hooks"


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------

def _make_executable(path: Path) -> None:
    """Add owner+group execute permission (no-op on Windows)."""
    if sys.platform == "win32":
        return
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IRGRP | stat.S_IROTH)


def _check_git_repo() -> None:
    """Abort early if we are not inside a Git repository."""
    if not HOOKS_DEST_DIR.exists():
        print(
            f"[install_hooks] ERROR: .git/hooks not found at {HOOKS_DEST_DIR}\n"
            "  Are you running this from the project root?",
            file=sys.stderr,
        )
        sys.exit(1)


def _check_source_dir() -> None:
    """Abort if the hooks source directory is missing."""
    if not HOOKS_SOURCE_DIR.exists():
        print(
            f"[install_hooks] ERROR: hooks source directory not found: {HOOKS_SOURCE_DIR}\n"
            "  Expected: scripts/hooks/",
            file=sys.stderr,
        )
        sys.exit(1)


# ----------------------------------------------------------------
# Main installer
# ----------------------------------------------------------------

def install_hooks() -> None:
    _check_git_repo()
    _check_source_dir()

    hook_files = [f for f in HOOKS_SOURCE_DIR.iterdir() if f.is_file()]

    if not hook_files:
        print("[install_hooks] No hook files found in scripts/hooks/. Nothing to install.")
        return

    print(f"[install_hooks] Installing {len(hook_files)} hook(s) into {HOOKS_DEST_DIR}\n")

    installed = []
    failed    = []

    for hook in sorted(hook_files):
        dest = HOOKS_DEST_DIR / hook.name
        try:
            shutil.copy2(hook, dest)
            _make_executable(dest)
            status = "updated" if dest.exists() else "installed"
            print(f"  OK  {hook.name:<20}  ->  {dest}")
            installed.append(hook.name)
        except Exception as exc:
            print(f"  FAIL {hook.name:<20}  ->  {exc}", file=sys.stderr)
            failed.append(hook.name)

    # Summary
    print(f"\n[install_hooks] Done. {len(installed)} installed, {len(failed)} failed.")

    if failed:
        print(
            "\n[install_hooks] Some hooks failed to install. "
            "Check file permissions and try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        "\n[install_hooks] All hooks active.\n"
        "  Tip: use  git commit --no-verify  to bypass hooks when needed."
    )


if __name__ == "__main__":
    install_hooks()
