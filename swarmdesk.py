#!/usr/bin/env python3
"""swarmdesk: one board for one manager and many AI or human sessions, on any harness.

The board is a folder of plain files. This CLI is the only writer of the shared ones:

    swarmdesk say FROM TO TYPE REF "one line"     post a clock-stamped line to today's channel
    swarmdesk hear ME [--peek|--all]               lines for ME (or ALL) not yet read
    swarmdesk watch ME [--until HH:MMZ]            block and print ME's lines as they land
    swarmdesk state ME < file | state --all        write your state, or glance at everyone's
    swarmdesk decide [--by ID] "text"              the manager's decision log
    swarmdesk handover ID new|append < file        handover notes, append-only after creation
    swarmdesk init --roster ... | roster [add] | doctor

The board is found from --board, then $SWARMDESK_BOARD, then the folder this file sits in (a board carries
its own copy of the CLI), then the nearest .swarmdesk/ above the working directory.
Time always comes from the clock; SWARMDESK_NOW pins it for tests only.
Exit codes: 0 done, 1 error or unhealthy, 2 refused or usage.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import time
from contextlib import contextmanager
from pathlib import Path

__version__ = "0.1.0"

HERE = Path(__file__).resolve().parent
RESERVED = {"ALL", "HUMAN"}
ROLES = ("manager", "worker", "reviewer", "runner")
DEFAULT_TYPES = ["STATUS", "ASK", "ANSWER", "BLOCKED", "CLAIM", "REVIEW-REQ", "REVIEW-RESULT",
                 "HANDOFF", "DONE", "DECISION"]
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,15}$")
REF_RE = re.compile(r"^(-|[A-Za-z0-9][A-Za-z0-9._/#-]{0,63})$")
LINE_RE = re.compile(r"^\d{2}:\d{2}:\d{2}Z \| (\S+) -> (\S+) \| (\S+) \| (\S+) \| ")
CREDENTIAL_RE = (
    r"eyJ[A-Za-z0-9_-]{20,}|bearer [A-Za-z0-9._-]{20,}"
    r"|(client_secret|api[_-]?key|password|passwd|refresh_token|access_token|secret)[\" ]*[:=][\" ]*[A-Za-z0-9/+._-]{8,}"
    r"|xox[bpa]-|ghp_[A-Za-z0-9]{20,}|github_pat_|glpat-|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|GOCSPX-|ya29\."
    r"|1//0[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN|ATATT3"
)
# A time written by hand instead of read from the clock ("14:1xZ", "09:xx").
PLACEHOLDER_TIME_RE = re.compile(r"\b\d{1,2}:\d?[xX]{1,2}Z?\b")


class Refused(Exception):
    """A request the protocol does not allow; exit code 2."""


# ---------------------------------------------------------------- clock


def now():
    pinned = os.environ.get("SWARMDESK_NOW")
    if pinned:
        return dt.datetime.fromisoformat(pinned.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)


def stamp(t=None):
    return (t or now()).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- locking


@contextmanager
def locked(path, timeout=10.0):
    """Exclusive cross-process lock on `path` (fcntl on Unix, msvcrt on Windows)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+b")
    deadline = time.monotonic() + timeout
    try:
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise Refused(f"lock {path.name} busy for {timeout:.0f} s, try again")
                    time.sleep(0.05)
        else:
            import fcntl
            while True:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > deadline:
                        raise Refused(f"lock {path.name} busy for {timeout:.0f} s, try again")
                    time.sleep(0.01)
        yield
    finally:
        if os.name == "nt":
            try:
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        fh.close()


def append(path, text):
    """One write of the whole text, so a reader never sees half a line."""
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)


# ---------------------------------------------------------------- board


class Board:
    def __init__(self, root, config):
        self.root = Path(root)
        self.config = config
        self.roster = {m["id"]: m for m in config["roster"]}
        self.types = config.get("types") or DEFAULT_TYPES
        self.line_cap = int(config.get("line_cap", 700))
        self.checkin = int(config.get("checkin_minutes", 15))
        extra = config.get("credential_patterns") or []
        self.credential_re = re.compile("|".join([CREDENTIAL_RE] + extra), re.IGNORECASE)

    @property
    def manager(self):
        return next(m["id"] for m in self.config["roster"] if m["role"] == "manager")

    def chat_file(self, day):
        return self.root / "chat" / f"{day}.md"

    def lock(self, name="chat"):
        return locked(self.root / f".{name}.lock")


def find_board(explicit=None):
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    elif os.environ.get("SWARMDESK_BOARD"):
        candidates.append(Path(os.environ["SWARMDESK_BOARD"]))
    else:
        candidates.append(HERE)
        cwd = Path.cwd().resolve()
        for d in [cwd, *cwd.parents]:
            candidates.append(d / ".swarmdesk")
    for c in candidates:
        if (c / "config.json").is_file():
            return c
    where = candidates[0] if explicit or os.environ.get("SWARMDESK_BOARD") else Path.cwd()
    raise Refused(f"no board found from {where}; run `swarmdesk init` or pass --board")


def load_board(root):
    root = Path(root)
    try:
        config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Refused(f"no config.json in {root}")
    return Board(root, config)


def validate_roster(roster):
    seen = set()
    for m in roster:
        mid = m["id"]
        if mid.upper() in RESERVED:
            raise Refused(f"id {mid} is reserved (ALL and HUMAN are addresses, not sessions)")
        if not ID_RE.match(mid):
            raise Refused(f"id {mid!r}: use a letter then up to 15 letters, digits, _ or -")
        if mid in seen:
            raise Refused(f"duplicate id {mid}")
        seen.add(mid)
        if m["role"] not in ROLES:
            raise Refused(f"{mid}: role {m['role']!r} is not one of {', '.join(ROLES)}")
    if sum(1 for m in roster if m["role"] == "manager") != 1:
        raise Refused("the roster needs exactly one manager")


def parse_roster(spec):
    out = []
    for item in [s.strip() for s in spec.split(",") if s.strip()]:
        parts = item.split(":")
        if len(parts) not in (2, 3):
            raise Refused(f"roster item {item!r}: use ID:role or ID:role:harness")
        out.append({"id": parts[0], "role": parts[1], "harness": parts[2] if len(parts) == 3 else "any"})
    validate_roster(out)
    return out


# ---------------------------------------------------------------- say / hear


def say(board, frm, to, typ, ref, text):
    """Validate and append one line; returns the line."""
    if frm not in board.roster:
        raise Refused(f"FROM {frm} is not on the roster ({', '.join(board.roster)})")
    if re.search(r"[,;+\s]", to):
        raise Refused(f"TO {to!r}: one recipient per line; post one line to each, or to ALL")
    if to not in board.roster and to not in RESERVED:
        raise Refused(f"TO {to} is not on the roster and is not ALL or HUMAN")
    if to == "HUMAN" and board.roster[frm]["role"] != "manager":
        raise Refused("only the manager writes to HUMAN; send it to the manager as an ASK")
    if typ not in board.types:
        raise Refused(f"TYPE {typ} is not one of {', '.join(board.types)}")
    if not REF_RE.match(ref):
        raise Refused(f"REF {ref!r}: a ticket key, a repo name, a path-like token, or -")
    if "\n" in text or "\r" in text:
        raise Refused("one line only; put detail in a file under reviews/ and give its path")
    if not text.strip():
        raise Refused("empty text")
    if len(text) > board.line_cap:
        raise Refused(f"{len(text)} characters, the limit is {board.line_cap}; put detail in a file and give its path")
    if board.credential_re.search(text):
        raise Refused("the text looks like it carries a credential; never put one in the channel")
    if PLACEHOLDER_TIME_RE.search(text):
        raise Refused("that looks like a time written by hand; read the clock, or leave the time out")
    t = now()
    line = f"{t:%H:%M:%S}Z | {frm} -> {to} | {typ} | {ref} | {text.replace('|', '/')}"
    with board.lock():
        path = board.chat_file(f"{t:%Y-%m-%d}")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            append(path, f"# swarmdesk channel, {t:%Y-%m-%d} (UTC)\n\n"
                         "One line per message: time | from -> to | type | ref | text. Written only by `swarmdesk say`.\n\n")
        append(path, line + "\n")
    return line


def _readers(board):
    return set(board.roster) | {"HUMAN"}


def hear(board, me, mode=None):
    """New lines for `me` (or every new line with mode='all'); advances the cursor unless mode='peek'."""
    if me not in _readers(board):
        raise Refused(f"{me} is not on the roster (or HUMAN)")
    t = now()
    out = []
    cursors = board.root / ".cursor"
    cursors.mkdir(exist_ok=True)
    for day in [(t - dt.timedelta(days=1)).strftime("%Y-%m-%d"), t.strftime("%Y-%m-%d")]:
        path = board.chat_file(day)
        if not path.exists():
            continue
        cur = cursors / f"{me}-{day}"
        seen = int(cur.read_text() or 0) if cur.exists() else 0
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= seen:
            continue
        for line in lines[seen:]:
            m = LINE_RE.match(line)
            if not m:
                continue
            # ALL is a broadcast to the sessions; HUMAN hears only what the manager sends HUMAN.
            if mode == "all" or m.group(2) == me or (m.group(2) == "ALL" and me != "HUMAN"):
                out.append(line)
        if mode != "peek":
            cur.write_text(str(len(lines)))
    return out


# ---------------------------------------------------------------- state / decide / handover


STATE_HEAD = re.compile(r"^<!-- swarmdesk state (\S+) written (\S+) -->")


def write_state(board, me, text):
    if me not in board.roster:
        raise Refused(f"{me} is not on the roster")
    path = board.root / "state" / f"{me}.md"
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(f"<!-- swarmdesk state {me} written {stamp()} -->\n{text}", encoding="utf-8")
    os.replace(tmp, path)
    return path


def glance(board):
    t = now()
    stale_after = 2 * board.checkin
    rows = []
    for mid, m in board.roster.items():
        path = board.root / "state" / f"{mid}.md"
        age = "never"
        flag = ""
        first = ""
        if path.exists():
            head = path.read_text(encoding="utf-8").splitlines()
            hm = STATE_HEAD.match(head[0]) if head else None
            if hm:
                written = dt.datetime.fromisoformat(hm.group(2).replace("Z", "+00:00"))
                minutes = int((t - written).total_seconds() // 60)
                age = f"{minutes} min"
                if minutes > stale_after:
                    flag = "STALE"
                first = next((l.strip() for l in head[1:] if l.strip() and not l.startswith("#")), "")
        rows.append(f"{mid:<16} {age:<10} {flag:<6} {m['role']:<9} {first[:80]}")
    return rows


def decide(board, by, text):
    if by not in board.roster:
        raise Refused(f"{by} is not on the roster")
    if "\n" in text.strip():
        raise Refused("one decision per line")
    line = f"- {now():%Y-%m-%d %H:%M:%S}Z | {by} | {text.strip()}"
    with board.lock("decisions"):
        append(board.root / "decisions.md", line + "\n")
    return line


def handover(board, who, action, text):
    if who not in board.roster:
        raise Refused(f"{who} is not on the roster")
    folder = board.root / "handovers"
    folder.mkdir(exist_ok=True)
    existing = sorted(folder.glob(f"{who}-*.md"))
    t = now()
    if action == "new":
        path = folder / f"{who}-{t:%Y-%m-%d-%H%M}.md"
        if path.exists():
            raise Refused(f"{path.name} exists; append to it")
        template = template_text("handover.md").replace("{ID}", who).replace("{WHEN}", f"{t:%Y-%m-%d %H:%M:%S}Z")
        path.write_text(template + ("\n" + text if text.strip() else ""), encoding="utf-8")
        return path
    if not existing:
        raise Refused(f"no handover for {who} yet; start one with `handover {who} new`")
    path = existing[-1]
    append(path, f"\n## Update {t:%Y-%m-%d %H:%M:%S}Z\n\n{text.rstrip()}\n")
    return path


# ---------------------------------------------------------------- init / roster / doctor


def template_text(name):
    for base in (HERE / "templates",):
        p = base / name
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise Refused(f"template {name} not found next to {HERE}")


def render_readme(board):
    cfg = board.config
    rows = "\n".join(f"| {m['id']} | {m['role']} | {m.get('harness', 'any')} | `briefs/{m['id']}.md` |"
                     for m in cfg["roster"])
    return template_text("board-readme.md").format(
        human=cfg.get("human", "the human"), manager=board.manager, roster=rows,
        checkin=board.checkin, line_cap=board.line_cap, types=", ".join(board.types),
        profile=cfg.get("profile", "generic"))


def write_brief(board, member):
    path = board.root / "briefs" / f"{member['id']}.md"
    if not path.exists():
        role_file = f"brief-{member['role']}.md"
        body = template_text(role_file if (HERE / "templates" / role_file).exists() else "brief.md")
        path.write_text(body.replace("{ID}", member["id"]).replace("{ROLE}", member["role"])
                        .replace("{MANAGER}", board.manager), encoding="utf-8")


def init(root, roster_spec, human, profile, checkin, force_dir=False):
    root = Path(root)
    if (root / "config.json").exists():
        raise Refused(f"{root} already holds a board; use `roster add` to grow it")
    roster = parse_roster(roster_spec)
    profile_src = HERE / "profiles" / f"{profile}.md"
    if profile != "generic" and not profile_src.exists():
        raise Refused(f"profile {profile!r} not found in {HERE / 'profiles'}")
    for sub in ["chat", "state", "briefs", "reviews", "handovers", ".cursor"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    config = {"swarmdesk": __version__, "human": human, "profile": profile, "checkin_minutes": checkin,
              "line_cap": 700, "types": DEFAULT_TYPES, "credential_patterns": [], "roster": roster}
    (root / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    if Path(__file__).resolve() != (root / "swarmdesk.py").resolve():
        shutil.copy2(Path(__file__).resolve(), root / "swarmdesk.py")
    if (HERE / "templates").resolve() != (root / "templates").resolve():
        shutil.copytree(HERE / "templates", root / "templates", dirs_exist_ok=True)
    if profile_src.exists():
        (root / "profiles").mkdir(exist_ok=True)
        shutil.copy2(profile_src, root / "profiles" / profile_src.name)
        shutil.copy2(profile_src, root / "PROFILE.md")
    board = load_board(root)
    (root / "README.md").write_text(render_readme(board), encoding="utf-8")
    for m in roster:
        write_brief(board, m)
    for name, tpl in [("decisions.md", "decisions.md"), ("for-human.md", "for-human.md")]:
        if not (root / name).exists():
            (root / name).write_text(template_text(tpl).replace("{HUMAN}", human), encoding="utf-8")
    return board


def roster_add(board, mid, role, harness):
    roster = board.config["roster"] + [{"id": mid, "role": role, "harness": harness}]
    validate_roster(roster)
    board.config["roster"] = roster
    with board.lock("config"):
        tmp = board.root / "config.json.tmp"
        tmp.write_text(json.dumps(board.config, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, board.root / "config.json")
    board = load_board(board.root)
    write_brief(board, board.roster[mid])
    (board.root / "README.md").write_text(render_readme(board), encoding="utf-8")
    return board


def doctor(board):
    problems, notes = [], []
    try:
        validate_roster(board.config["roster"])
    except Refused as e:
        problems.append(f"roster: {e}")
    for sub in ["chat", "state", "briefs", "reviews", "handovers"]:
        p = board.root / sub
        if not p.is_dir():
            problems.append(f"missing folder {sub}/")
        elif not os.access(p, os.W_OK):
            problems.append(f"{sub}/ is not writable")
    for path in sorted((board.root / "chat").glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for n, line in enumerate(lines, 1):
            if line[:2].isdigit() and not LINE_RE.match(line):
                problems.append(f"{path.name}:{n} is not a channel line (written by hand?)")
            if board.credential_re.search(line):
                problems.append(f"{path.name}:{n} looks like it carries a credential; remove it and rotate it")
        for cur in (board.root / ".cursor").glob(f"*-{path.stem}"):
            if int(cur.read_text() or 0) > len(lines):
                problems.append(f"cursor {cur.name} is past the end of {path.name}")
    notes.append(f"clock now {stamp()}, board {board.root}, {len(board.roster)} sessions, manager {board.manager}")
    return problems, notes


# ---------------------------------------------------------------- CLI


def build_parser():
    p = argparse.ArgumentParser(prog="swarmdesk", description="One board for one manager and many sessions.")
    p.add_argument("--board", help="path to the board folder (default: found automatically)")
    p.add_argument("--version", action="version", version=f"swarmdesk {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("say", help="post one line")
    for a in ["frm", "to", "type", "ref", "text"]:
        s.add_argument(a)

    h = sub.add_parser("hear", help="read your new lines")
    h.add_argument("me")
    g = h.add_mutually_exclusive_group()
    g.add_argument("--peek", action="store_true", help="do not advance your cursor")
    g.add_argument("--all", action="store_true", help="every new line, whoever it is for (the manager's sweep)")

    w = sub.add_parser("watch", help="block and print your lines as they land")
    w.add_argument("me")
    w.add_argument("--until", help="stop at this UTC time, HH:MMZ")
    w.add_argument("--max-lines", type=int, help="stop after this many lines")
    w.add_argument("--interval", type=float, default=2.0, help="seconds between checks")
    w.add_argument("--all", action="store_true")

    st = sub.add_parser("state", help="write your state from stdin or a file, or --all to glance")
    st.add_argument("me", nargs="?")
    st.add_argument("--from", dest="src", help="read the state from this file instead of stdin")
    st.add_argument("--all", action="store_true")

    d = sub.add_parser("decide", help="append to the decision log")
    d.add_argument("--by", help="who decided (default: the manager)")
    d.add_argument("text")

    ho = sub.add_parser("handover", help="start or append a handover (text from stdin or --from)")
    ho.add_argument("who")
    ho.add_argument("action", choices=["new", "append"])
    ho.add_argument("--from", dest="src")

    i = sub.add_parser("init", help="create a board")
    i.add_argument("--roster", required=True, help="ID:role[:harness],... with exactly one manager")
    i.add_argument("--human", default="the human", help="how the board names its human")
    i.add_argument("--profile", default="generic")
    i.add_argument("--checkin", type=int, default=15, help="minutes between checks of the channel")

    r = sub.add_parser("roster", help="list the roster, or add a session")
    r.add_argument("action", nargs="?", choices=["add"])
    r.add_argument("id", nargs="?")
    r.add_argument("role", nargs="?")
    r.add_argument("harness", nargs="?", default="any")

    sub.add_parser("doctor", help="check the board's health")
    return p


def read_input(src):
    if src:
        return Path(src).read_text(encoding="utf-8")
    return "" if sys.stdin.isatty() else sys.stdin.read()


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "init":
            root = Path(args.board) if args.board else Path.cwd() / ".swarmdesk"
            board = init(root, args.roster, args.human, args.profile, args.checkin)
            print(f"board ready at {board.root}")
            print(f"every session runs: python3 {board.root / 'swarmdesk.py'} hear <ID>")
            return 0
        board = load_board(find_board(args.board))
        if args.cmd == "say":
            print(say(board, args.frm, args.to, args.type, args.ref, args.text))
        elif args.cmd == "hear":
            for line in hear(board, args.me, "peek" if args.peek else "all" if args.all else None):
                print(line)
        elif args.cmd == "watch":
            shown = 0
            while True:
                for line in hear(board, args.me, "all" if args.all else None):
                    print(line, flush=True)
                    shown += 1
                    if args.max_lines and shown >= args.max_lines:
                        return 0
                if args.until and f"{now():%H:%M}Z" >= args.until.upper().rstrip("Z") + "Z":
                    return 0
                time.sleep(args.interval)
        elif args.cmd == "state":
            if args.all:
                print(f"{'ID':<16} {'AGE':<10} {'FLAG':<6} {'ROLE':<9} FIRST LINE")
                for row in glance(board):
                    print(row)
            elif not args.me:
                raise Refused("state needs your ID, or --all")
            else:
                print(write_state(board, args.me, read_input(args.src)))
        elif args.cmd == "decide":
            print(decide(board, args.by or board.manager, args.text))
        elif args.cmd == "handover":
            print(handover(board, args.who, args.action, read_input(args.src)))
        elif args.cmd == "roster":
            if args.action == "add":
                if not (args.id and args.role):
                    raise Refused("roster add ID ROLE [HARNESS]")
                roster_add(board, args.id, args.role, args.harness)
                print(f"added {args.id}; its brief is briefs/{args.id}.md")
            else:
                for m in board.config["roster"]:
                    print(f"{m['id']:<16} {m['role']:<9} {m.get('harness', 'any')}")
        elif args.cmd == "doctor":
            problems, notes = doctor(board)
            for n in notes:
                print(n)
            for pr in problems:
                print(f"PROBLEM: {pr}")
            print("healthy" if not problems else f"{len(problems)} problem(s)")
            return 0 if not problems else 1
        return 0
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
