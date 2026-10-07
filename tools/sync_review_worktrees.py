"""Split the integrated, uncommitted review into existing feature worktrees.

Run with --apply to copy files. No commits, staging, pushes or recursive deletes.
The integration checkout remains the runnable source of truth until review ends.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/uiux-v2-branches.json"
BRANCHES = {
    "foundation": "feature/uiux-v2-foundation",
    "attendee": "feature/uiux-v2-attendee",
    "operations": "feature/uiux-v2-operations",
    "backend": "feature/backend-realtime-lifecycle",
    "docs": "feature/uiux-v2-documentation",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE).decode("utf-8").strip()


def owner(path: str) -> str:
    if path.startswith("Backend/"):
        return "backend"
    if path.startswith(("docs/", "Frontend/docs/")) or path in {"readme.md", "Frontend/README.md"}:
        return "docs"
    if path.startswith(("Frontend/src/pages/attendee/", "Frontend/src/pages/auth/",
                        "Frontend/src/features/tickets/", "Frontend/src/features/events/")):
        return "attendee"
    if path in {"Frontend/src/styles/attendee.css", "Frontend/src/styles/auth.css"}:
        return "attendee"
    if path.startswith(("Frontend/src/pages/organizer/", "Frontend/src/pages/staff/",
                        "Frontend/src/features/organizer/", "Frontend/src/features/door/",
                        "Frontend/src/features/live/", "Frontend/src/features/realtime/",
                        "Frontend/src/features/notifications/", "Frontend/src/realtime/",
                        "Frontend/tests/")):
        return "operations"
    if path in {"Frontend/src/styles/operations.css", "Frontend/src/styles/organizer.css"}:
        return "operations"
    return "foundation"


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    worktrees = {}
    for block in git("worktree", "list", "--porcelain").split("\n\n"):
        rows = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        branch = rows.get("branch", "").removeprefix("refs/heads/")
        if branch in BRANCHES.values():
            worktrees[branch] = Path(rows["worktree"]).resolve()
    assert set(BRANCHES.values()) <= worktrees.keys(), "Create the five feature worktrees first"
    assert ROOT not in worktrees.values(), "Run from the integration checkout"
    dirty_paths = {}
    for branch, directory in worktrees.items():
        tracked = subprocess.check_output(["git", "-C", str(directory), "diff", "HEAD", "--name-only", "-z"], stderr=subprocess.PIPE)
        untracked = subprocess.check_output(["git", "-C", str(directory), "ls-files", "--others", "--exclude-standard", "-z"])
        dirty_paths[branch] = set((tracked + untracked).decode("utf-8").split("\0")) - {""}
    files = set(git("diff", "HEAD", "--name-only", "-z").split("\0"))
    files.update(git("ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    files.discard("")
    # The manifest is metadata shared with the documentation branch, not a source diff.
    files.discard("docs/uiux-v2-branches.json")
    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    assert not previous.get("committed"), "Review already committed: do not overwrite published worktrees"
    old = {item["path"]: item for group in previous.get("groups", {}).values()
           for item in group.get("files", [])}
    # Reconcile previously copied untracked files that were removed during cleanup.
    files.update(path for path in old if not (ROOT / path).is_file())
    report = {"base_commit": git("rev-parse", "HEAD"), "integration_branch": git("branch", "--show-current"),
              "committed": False, "notes": "Scoped uncommitted diffs; frontend scopes depend on each other. Run and test from integration.",
              "groups": {key: {"branch": branch, "worktree": str(worktrees[branch]), "files": []}
                         for key, branch in BRANCHES.items()}}
    # Validate all paths and previous copies before any write.
    plan = []
    for relative in sorted(files):
        scope = owner(relative)
        source = (ROOT / relative).resolve()
        destination_root = worktrees[BRANCHES[scope]]
        destination = (destination_root / relative).resolve()
        assert source.is_relative_to(ROOT) and destination.is_relative_to(destination_root)
        source_hash = digest(source)
        if relative in old:
            assert digest(destination) in {old[relative]["sha256"], source_hash}, f"Worktree edited independently: {destination}"
        else:
            assert relative not in dirty_paths[BRANCHES[scope]] or digest(destination) == source_hash, f"Preserve existing worktree edit: {destination}"
        report["groups"][scope]["files"].append({"path": relative, "deleted": source_hash is None, "sha256": source_hash})
        plan.append((source, destination, source_hash))
    if args.apply:
        for source, destination, source_hash in plan:
            if source_hash is None:
                # Only remove an explicitly listed tracked file, never a directory.
                if destination.is_file():
                    destination.unlink()
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            assert digest(destination) == source_hash, f"Copy verification failed: {destination}"
        MANIFEST.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        documentation_manifest = worktrees[BRANCHES["docs"]] / "docs/uiux-v2-branches.json"
        documentation_manifest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MANIFEST, documentation_manifest)
    for scope, group in report["groups"].items():
        print(f'{group["branch"]}: {len(group["files"])} files ({"copied and verified" if args.apply else "plan only"})')


if __name__ == "__main__":
    main()
