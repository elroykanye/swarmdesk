#!/usr/bin/env python3
"""Install the swarmdesk skills into one or more agent harnesses.

    python3 scripts/install.py bindings                         harnesses known, and their verification status
    python3 scripts/install.py install [--target DIR | --scope user] [--binding auto|all|id,id] [--dry-run] [--force]
    python3 scripts/install.py status  [--target DIR | --scope user]
    python3 scripts/install.py uninstall [--target DIR | --scope user] [--dry-run]

One JSON file per harness in bindings/ says where that harness reads skills and in what format; there is no
per-harness code. A manifest records every file written with its hash, so `status` can tell a local edit from a
stale install, and `install` never overwrites a local edit without --force.

The binding model and rendering follow vince-gate's installer (https://github.com/elroykanye/vince-gate), cut down
to what swarmdesk needs. Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_BEGIN = "<!-- swarmdesk:begin -->"
INDEX_END = "<!-- swarmdesk:end -->"


def version():
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def load_bindings():
    out = {}
    for p in sorted((ROOT / "bindings").glob("*.json")):
        b = json.loads(p.read_text(encoding="utf-8"))
        out[b["id"]] = b
    return out


def skill_names():
    return sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file())


def split_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fields = {}
    for line in text[3:end].strip("\n").splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields, text[end + 4:].lstrip("\n")


def render_entry(binding, name, description, body):
    style = binding.get("frontmatter", "none")
    if style == "yaml":
        return f"---\nname: {name}\ndescription: {description}\n---\n\n{body}"
    if style == "mdc":
        return f"---\ndescription: {description}\nglobs:\nalwaysApply: false\n---\n\n{body}"
    if style == "windsurf":
        return f"---\ntrigger: model_decision\ndescription: {description}\n---\n\n{body}"
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines.insert(i + 1, f"\n> {description}")
            return "\n".join(lines)
    return f"> {description}\n\n{body}"


def render_skill(binding, skill):
    fields, body = split_frontmatter((ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8"))
    text = render_entry(binding, fields.get("name", skill), fields.get("description", ""), body)
    if binding.get("layout", "dir") == "dir":
        rel = f"{skill}/{binding.get('entry', 'SKILL.md')}"
    else:
        rel = f"{skill}{binding.get('extension', '.md')}"
    return rel, text.encode("utf-8")


def index_block(bindings, base):
    rows = []
    for s in skill_names():
        desc = split_frontmatter((ROOT / "skills" / s / "SKILL.md").read_text(encoding="utf-8"))[0].get("description", "")
        desc = desc.split(" - ")[0]
        where = "; ".join(f"`{(base / b['project_dir'] / render_skill(b, s)[0]).as_posix()}`" for b in bindings)
        rows.append(f"| `{s}` | {desc} | {where} |")
    return "\n".join([
        INDEX_BEGIN,
        "## swarmdesk: several sessions, one manager, one board",
        "",
        "If this project has a `.swarmdesk/` board, you work through it: read `.swarmdesk/README.md`, then the skill",
        "for your role below, then your brief in `.swarmdesk/briefs/`. Every approval goes to the manager.",
        "",
        "| Skill | Purpose | File |",
        "|---|---|---|",
        *rows,
        INDEX_END,
    ]) + "\n"


def write_index(path, block, dry_run):
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if INDEX_BEGIN in existing and INDEX_END in existing:
        start, end = existing.index(INDEX_BEGIN), existing.index(INDEX_END) + len(INDEX_END)
        updated = existing[:start] + block.rstrip("\n") + existing[end:]
    elif existing.strip():
        updated = existing.rstrip("\n") + "\n\n" + block
    else:
        updated = block
    if not dry_run:
        path.write_text(updated, encoding="utf-8")


def strip_index(path, dry_run):
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if INDEX_BEGIN not in text or INDEX_END not in text:
        return False
    start, end = text.index(INDEX_BEGIN), text.index(INDEX_END) + len(INDEX_END)
    updated = (text[:start].rstrip("\n") + "\n" + text[end:].lstrip("\n")).strip("\n")
    if not dry_run:
        if updated:
            path.write_text(updated + "\n", encoding="utf-8")
        else:
            path.unlink()
    return True


def sha(data):
    return hashlib.sha256(data).hexdigest()


def resolve(args):
    """Return (base directory, scope, manifest path)."""
    if args.scope == "user":
        home = Path(os.path.expanduser("~"))
        return home, "user", home / ".config" / "swarmdesk" / "install.json"
    base = Path(args.target or ".").resolve()
    return base, "project", base / ".swarmdesk-install.json"


def binding_dir(binding, base, scope):
    if scope == "user":
        if not binding.get("user_dir"):
            return None
        return Path(os.path.expanduser(binding["user_dir"].replace("~", str(base), 1)))
    return base / binding["project_dir"]


def choose(spec, base, scope, bindings):
    if spec == "all":
        return list(bindings.values())
    if spec != "auto":
        ids = [s.strip() for s in spec.split(",") if s.strip()]
        unknown = [i for i in ids if i not in bindings]
        if unknown:
            raise SystemExit(f"unknown binding(s): {', '.join(unknown)}; see `install.py bindings`")
        return [bindings[i] for i in ids]
    found = [b for b in bindings.values() if b["id"] != "generic" and any((base / d).exists() for d in b["detect"])]
    if scope == "project" and (base / "AGENTS.md").exists():
        found.append(bindings["generic"])
    return found or [bindings["generic"]]


def load_manifest(path):
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"version": None, "scope": None, "files": {}, "indexes": []}


def cmd_bindings(_args):
    for b in load_bindings().values():
        print(f"{b['id']:<9} {b['status']:<11} {b['label']}  ->  {b['project_dir']}"
              + (f"  (user: {b['user_dir']})" if b.get("user_dir") else "  (project scope only)"))
    return 0


def cmd_install(args):
    base, scope, mpath = resolve(args)
    bindings = load_bindings()
    chosen = choose(args.binding, base, scope, bindings)
    manifest = load_manifest(mpath)
    plan, conflicts = [], []
    for b in chosen:
        d = binding_dir(b, base, scope)
        if d is None:
            print(f"skip {b['id']}: it has no user-scope location; install it with --target <project>")
            continue
        for s in skill_names():
            rel, data = render_skill(b, s)
            path = d / rel
            key = str(path)
            if path.exists() and not args.force:
                current = sha(path.read_bytes())
                recorded = manifest["files"].get(key)
                if current != sha(data) and current != recorded:
                    conflicts.append(path)
            plan.append((path, data))
    if conflicts:
        for c in conflicts:
            print(f"refused: {c} was edited locally; keep your edit, or rerun with --force", file=sys.stderr)
        return 2
    for path, data in plan:
        print(("would write " if args.dry_run else "write ") + str(path))
        if not args.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            manifest["files"][str(path)] = sha(data)
    indexed = [b for b in chosen if b.get("index") and binding_dir(b, base, scope) is not None]
    if indexed and scope == "project":
        ipath = base / indexed[0]["index"]
        print(("would update " if args.dry_run else "update ") + str(ipath))
        write_index(ipath, index_block(indexed, Path(".")), args.dry_run)
        if str(ipath) not in manifest["indexes"]:
            manifest["indexes"].append(str(ipath))
    if not args.dry_run:
        manifest.update({"version": version(), "scope": scope})
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"swarmdesk {version()} installed for: {', '.join(b['id'] for b in chosen)}")
        for b in chosen:
            print(f"  {b['label']}: {b['invocation'].replace('{skill}', 'swarmdesk-<role>')} ({b['status']})")
    return 0


def cmd_status(args):
    base, scope, mpath = resolve(args)
    manifest = load_manifest(mpath)
    if not manifest["files"]:
        print(f"not installed ({mpath} not found)")
        return 1
    problems = []
    for path, recorded in sorted(manifest["files"].items()):
        p = Path(path)
        if not p.exists():
            problems.append(f"missing  {path}")
        elif sha(p.read_bytes()) != recorded:
            problems.append(f"edited   {path}")
    if manifest.get("version") != version():
        problems.append(f"stale    installed {manifest.get('version')}, this checkout is {version()}; rerun install")
    for line in problems:
        print(line)
    print(f"swarmdesk {manifest.get('version')} ({scope}): " + ("healthy" if not problems else f"{len(problems)} problem(s)"))
    return 0 if not problems else 1


def cmd_uninstall(args):
    base, scope, mpath = resolve(args)
    manifest = load_manifest(mpath)
    for path in sorted(manifest["files"]):
        p = Path(path)
        if p.exists():
            print(("would remove " if args.dry_run else "remove ") + path)
            if not args.dry_run:
                p.unlink()
                parent = p.parent
                while parent != base and parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
    for ipath in manifest.get("indexes", []):
        if strip_index(Path(ipath), args.dry_run):
            print(("would clean " if args.dry_run else "clean ") + ipath)
    if not args.dry_run and mpath.exists():
        mpath.unlink()
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="install.py", description="Install the swarmdesk skills into agent harnesses.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bindings", help="list known harnesses")
    for name in ("install", "status", "uninstall"):
        s = sub.add_parser(name)
        s.add_argument("--target", help="project folder (default: the current directory)")
        s.add_argument("--scope", choices=("project", "user"), default="project")
        if name == "install":
            s.add_argument("--binding", default="auto", help="auto (detect), all, or a comma list of ids")
            s.add_argument("--force", action="store_true", help="overwrite files edited locally")
        if name in ("install", "uninstall"):
            s.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    return {"bindings": cmd_bindings, "install": cmd_install, "status": cmd_status,
            "uninstall": cmd_uninstall}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
