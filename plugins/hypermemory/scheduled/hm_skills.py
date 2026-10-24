#!/usr/bin/env python3
"""Keep the HyperMemory-published skills installed in Claude up to date.

Used by the HyperMemory nightly update check. Three commands:

  inventory   List the skills installed in the Claude skills folder (and, read
              only, the skills Claude syncs from the claude.ai account), each
              with its bundle digest and install record.
  record      Write the install record for an installed skill whose files
              already match a published skill (adopts a hand-installed copy).
  install     Replace an installed skill with the published copy saved from
              hm_skill(action="get", include_content=true). Every file and the
              whole bundle are checked against the published SHA-256 digests
              before anything is written; the old copy is backed up first.

Digests follow the server (product-application skill_bundle.rs): a skill with
no supporting documents is the SHA-256 of SKILL.md; otherwise the SHA-256 of
"hypermemory-agent-skill-bundle-v1\n", then "SKILL.md <sha>\n", then
"<path> <sha>\n" for every document in byte order of the path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

HOME = Path.home()
SKILLS_DIR = HOME / ".claude" / "skills"
SYNCED_DIR = SKILLS_DIR / "synced"
BACKUP_DIR = HOME / ".claude" / "skill-backups"
RECORD = ".hypermemory-skill.json"
SKILL_FILE = "SKILL.md"
BUNDLE_HEADER = b"hypermemory-agent-skill-bundle-v1\n"
IGNORED_NAMES = {RECORD, ".DS_Store"}
BACKUPS_KEPT = 5

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bundle_sha256(skill_sha: str, files: dict[str, str]) -> str:
    if not files:
        return skill_sha
    manifest = hashlib.sha256(BUNDLE_HEADER)
    manifest.update(f"{SKILL_FILE} {skill_sha}\n".encode())
    for path in sorted(files, key=lambda p: p.encode()):
        manifest.update(f"{path} {files[path]}\n".encode())
    return manifest.hexdigest()


def frontmatter_field(text: str, field: str) -> str | None:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == field:
            return value.strip().strip("'\"") or None
    return None


def local_bundle(skill_dir: Path) -> dict:
    """Digest of an installed skill directory, computed like the server's."""
    skill_md = (skill_dir / SKILL_FILE).read_bytes()
    files: dict[str, str] = {}
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.name in IGNORED_NAMES:
            continue
        rel = path.relative_to(skill_dir).as_posix()
        if rel == SKILL_FILE:
            continue
        files[rel] = sha256_bytes(path.read_bytes())
    text = skill_md.decode("utf-8", errors="replace")
    return {
        "name": frontmatter_field(text, "name") or skill_dir.name,
        "frontmatter_version": frontmatter_field(text, "version"),
        "sha256": bundle_sha256(sha256_bytes(skill_md), files),
        "file_count": len(files),
    }


def read_record(skill_dir: Path) -> dict | None:
    path = skill_dir / RECORD
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"error": f"unreadable install record: {error}"}


def describe(skill_dir: Path, writable: bool) -> dict:
    entry = {"dir": str(skill_dir), "writable": writable, "symlink": skill_dir.is_symlink()}
    try:
        entry.update(local_bundle(skill_dir))
    except OSError as error:
        entry["error"] = f"could not read skill: {error}"
        return entry
    record = read_record(skill_dir)
    entry["record"] = record
    if record and "sha256" in record:
        entry["edited_since_install"] = record["sha256"] != entry["sha256"]
    return entry


def cmd_inventory(args: argparse.Namespace) -> int:
    skills_dir = Path(args.skills_dir)
    installed = []
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            if child.name == SYNCED_DIR.name or not (child / SKILL_FILE).is_file():
                continue
            installed.append(describe(child, writable=True))
    synced = []
    synced_dir = Path(args.synced_dir)
    if synced_dir.is_dir():
        for skill_md in sorted(synced_dir.glob(f"*/*/{SKILL_FILE}")):
            synced.append(describe(skill_md.parent, writable=False))
    json.dump({"skills_dir": str(skills_dir), "installed": installed, "synced_readonly": synced}, sys.stdout, indent=2)
    print()
    return 0


def load_published(path: Path) -> dict:
    """The skill object from a saved hm_skill get result (or the bare skill)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    skill = data.get("skill", data) if isinstance(data, dict) else None
    if not isinstance(skill, dict) or not isinstance(skill.get("content"), str):
        raise ValueError("no skill content found: save hm_skill get with include_content=true")
    for key in ("name", "sha256", "skill_id", "version"):
        if not skill.get(key):
            raise ValueError(f"published skill is missing '{key}'")
    return skill


def safe_relative(path: str) -> PurePosixPath:
    rel = PurePosixPath(path)
    if rel.is_absolute() or not rel.parts or ".." in rel.parts or rel.name in IGNORED_NAMES or str(rel) == SKILL_FILE:
        raise ValueError(f"refusing unsafe document path: {path!r}")
    return rel


def verify_published(skill: dict) -> dict[PurePosixPath, bytes]:
    """Check every document and the whole bundle against the published digests."""
    skill_md = skill["content"].encode("utf-8")
    documents: dict[PurePosixPath, bytes] = {}
    digests: dict[str, str] = {}
    for entry in skill.get("files") or []:
        if not isinstance(entry.get("content"), str):
            raise ValueError(f"document {entry.get('path')!r} has no text content in the saved result")
        rel = safe_relative(entry["path"])
        data = entry["content"].encode("utf-8")
        actual = sha256_bytes(data)
        if actual != entry.get("sha256"):
            raise ValueError(f"document {entry['path']} digest {actual} does not match published {entry.get('sha256')}")
        documents[rel] = data
        digests[rel.as_posix()] = actual
    bundle = bundle_sha256(sha256_bytes(skill_md), digests)
    if bundle != skill["sha256"]:
        raise ValueError(f"bundle digest {bundle} does not match published {skill['sha256']}")
    documents[PurePosixPath(SKILL_FILE)] = skill_md
    return documents


def make_record(skill: dict) -> dict:
    organization = skill.get("organization") or None
    return {
        "source": "hypermemory",
        "skill_id": skill["skill_id"],
        "name": skill["name"],
        "version": skill["version"],
        "revision": skill.get("revision"),
        "scope": skill.get("scope"),
        "organization": organization,
        "sha256": skill["sha256"],
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def write_record(skill_dir: Path, record: dict) -> None:
    (skill_dir / RECORD).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def installed_dir(skills_dir: Path, name: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        raise ValueError(f"refusing skill name {name!r}")
    target = skills_dir / name
    if not (target / SKILL_FILE).is_file():
        raise ValueError(f"{target} is not an installed skill; only installed skills are updated")
    if target.is_symlink():
        raise ValueError(f"{target} is a symlink; update its source instead")
    return target


def prune_backups(skill_backups: Path) -> None:
    kept = sorted((p for p in skill_backups.iterdir() if p.is_dir()), reverse=True)
    for old in kept[BACKUPS_KEPT:]:
        shutil.rmtree(old)


def cmd_install(args: argparse.Namespace) -> int:
    skill = load_published(Path(args.published_json))
    target = installed_dir(Path(args.skills_dir), skill["name"])
    current = describe(target, writable=True)
    record = current.get("record")
    if current.get("edited_since_install"):
        raise ValueError(f"{target} was edited after it was installed; not overwriting local changes")
    if record and record.get("skill_id") not in (None, skill["skill_id"]):
        raise ValueError(f"{target} was installed from skill_id {record['skill_id']}, not {skill['skill_id']}")
    if current["sha256"] == skill["sha256"]:
        write_record(target, make_record(skill))
        print(json.dumps({"result": "already_current", "dir": str(target), "version": skill["version"]}))
        return 0
    documents = verify_published(skill)

    staging = Path(tempfile.mkdtemp(prefix=f".{skill['name']}-", dir=target.parent))
    try:
        for rel, data in documents.items():
            path = staging.joinpath(*rel.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if describe(staging, writable=True)["sha256"] != skill["sha256"]:
            raise ValueError("written copy does not match the published digest")
        write_record(staging, make_record(skill))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        skill_backups = Path(args.backup_dir) / skill["name"]
        skill_backups.mkdir(parents=True, exist_ok=True)
        backup = skill_backups / stamp
        shutil.move(str(target), str(backup))
        os.replace(staging, target)
        prune_backups(skill_backups)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps({
        "result": "updated",
        "dir": str(target),
        "from": {"version": (record or {}).get("version") or current.get("frontmatter_version"), "sha256": current["sha256"]},
        "to": {"version": skill["version"], "revision": skill.get("revision"), "sha256": skill["sha256"]},
        "backup": str(backup),
    }))
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    target = installed_dir(Path(args.skills_dir), args.name)
    current = describe(target, writable=True)
    if current["sha256"] != args.sha256:
        raise ValueError(f"{target} digest {current['sha256']} does not match published {args.sha256}; not recording")
    organization = None
    if args.organization_id:
        organization = {"organization_id": args.organization_id, "name": args.organization_name}
    write_record(target, {
        "source": "hypermemory",
        "skill_id": args.skill_id,
        "name": args.name,
        "version": args.version,
        "revision": args.revision,
        "scope": args.scope,
        "organization": organization,
        "sha256": args.sha256,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    print(json.dumps({"result": "recorded", "dir": str(target), "version": args.version}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skills-dir", default=str(SKILLS_DIR))
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("inventory", help="list installed skills with digests and install records")
    inventory.add_argument("--synced-dir", default=str(SYNCED_DIR))
    inventory.set_defaults(run=cmd_inventory)

    install = sub.add_parser("install", help="update an installed skill from a saved hm_skill get result")
    install.add_argument("published_json", help="file holding the hm_skill get result (include_content=true)")
    install.add_argument("--backup-dir", default=str(BACKUP_DIR))
    install.set_defaults(run=cmd_install)

    record = sub.add_parser("record", help="record an installed skill that already matches a published skill")
    record.add_argument("name")
    for flag in ("--skill-id", "--version", "--sha256", "--scope"):
        record.add_argument(flag, required=True)
    record.add_argument("--revision", type=int)
    record.add_argument("--organization-id")
    record.add_argument("--organization-name")
    record.set_defaults(run=cmd_record)

    args = parser.parse_args()
    try:
        return args.run(args)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"result": "error", "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
