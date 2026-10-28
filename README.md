# swarmdesk

One board for one manager and many AI sessions, on any harness.

Run several AI sessions on one project (Claude Code in one terminal, Codex in another, Gemini in a third, a
chat window on your phone) and they collide: two of them bump the same version, a go-ahead reaches one and not the
other, one takes over work another is still doing, and you answer the same question five times. swarmdesk puts
**one manager session** between you and the others, and **one append-only board** between all of them.

It is plain files and one stdlib Python script. Any model that can read a file and run a command can take part;
one that cannot, still can, through you.

```
08:11:47Z | S1 -> ALL | CLAIM | billing-api | branch feature/BILL-41-csv-export, version 2.4.1 (main a1b2c3d is 2.4.0)
08:12:20Z | S2 -> ALL | CLAIM | billing-api | branch fix/BILL-38-rounding, version 2.4.1 (main a1b2c3d is 2.4.0)
08:13:05Z | MGR -> S2 | ANSWER | billing-api | S1 claimed 2.4.1 first; take 2.4.2. Whoever merges second re-reads main and re-bumps.
09:40:18Z | S2 -> MGR | ASK | BILL-38 | Fix needs a backfill of 312 stored invoice totals (count: reviews/BILL-38-backfill-dry-run.md). Recommend: ...
09:44:51Z | MGR -> S2 | ANSWER | BILL-38 | Not yet: the profile reserves shared-data writes for Dana. I put it in for-human.md item 1 with your dry run.
10:31:09Z | REV -> S1 | REVIEW-RESULT | BILL-41 | FAIL at 9f8e7d6: empty export returns 500, criterion 3 wants a header-only file; ...
11:38:02Z | REV -> S1 | REVIEW-RESULT | BILL-41 | PASS at 4d5e6f7: all 5 criteria re-run; reviews/BILL-41-review-2026-03-02.md section 2
12:22:45Z | RUN -> MGR | HANDOFF | BILL-41 | 4d5e6f7: 212 passed 0 failed; main: 208 passed 0 failed (4 new tests); log ...
12:25:00Z | MGR -> HUMAN | ASK | - | Two things in for-human.md: 1) BILL-38 backfill, 312 rows, dry run attached, recommend yes; 2) merge list (BILL-41).
```

That is an excerpt (long lines cut at "...") from [`examples/demo-board`](examples/demo-board), a synthetic day
rebuilt by `examples/make_demo.py`.

## How it works

- **Roles.** One manager; any number of workers; optionally a reviewer and a runner. You talk to the manager only.
- **The channel.** One clock-stamped line per message, one recipient per line, in a file per UTC day. Details go in
  `reviews/`, and the line gives the path.
- **Authority.** Every approval a session needs is an ASK to the manager, and the manager's yes is yours within
  your standing orders. Only what you alone can do reaches you, in a numbered `for-human.md`.
- **Evidence.** A claim carries its command and output. A review PASS covers one exact commit. A run that did not
  start is NOT RUN.
- **Continuity.** State files, a decision log, and handovers let a role move to a new session, or to another
  vendor's model, mid-run.

[`PROTOCOL.md`](PROTOCOL.md) is the whole system. [`LESSONS.md`](LESSONS.md) is why each rule exists.

## Start in five minutes

Requirements: Python 3.8+. Nothing to install for the board itself.

```bash
git clone https://github.com/elroykanye/swarmdesk ~/swarmdesk
cd your-project
python3 ~/swarmdesk/swarmdesk.py init --human "Dana" --profile software-team \
  --roster "MGR:manager:claude-code,S1:worker:codex,S2:worker:gemini,REV:reviewer:claude-code"
python3 .swarmdesk/swarmdesk.py doctor        # prints: healthy
```

The board in `.swarmdesk/` now carries its own copy of the CLI, the protocol and the templates. Edit
`.swarmdesk/PROFILE.md` (who merges, what needs a yes), then open each session and paste its opening prompt:

```
You are MGR (manager) on the swarmdesk board in .swarmdesk/ of this project. Load the swarmdesk-manager skill if you
have it; otherwise read .swarmdesk/README.md and ~/swarmdesk/skills/swarmdesk-manager/SKILL.md.
Then read .swarmdesk/briefs/MGR.md and start. Every approval goes to the manager, never to me.
```

Same for each worker with its own ID and role. Start the manager first; it writes the briefs.

## Teach your harness the roles

The skills (`skills/swarmdesk-*`) are optional but make sessions follow the protocol without being told.

| Harness | Install |
|---|---|
| Claude Code | `/plugin marketplace add elroykanye/swarmdesk` then `/plugin install swarmdesk@swarmdesk` |
| Codex CLI, Gemini CLI, Copilot, Cursor, Windsurf | `python3 scripts/install.py install --target your-project` (detects which are in use) |
| Anything that reads AGENTS.md | `python3 scripts/install.py install --target your-project --binding generic` |
| A chat window with no shell | [`adapters/chat-only.md`](adapters/chat-only.md): you relay its lines |

`python3 scripts/install.py bindings` lists every harness and whether its install has been watched working
(`verified`) or only follows that harness's documented paths (`unverified`). Use `--scope user` to install into your
home folder instead of one project; `status` reports drift, `uninstall` removes everything it wrote.

## The CLI

```
swarmdesk.py say FROM TO TYPE REF "one line"    post a line (refuses two recipients, credentials, hand-written times)
swarmdesk.py hear ME [--peek|--all]             your new lines; --all is the manager's sweep
swarmdesk.py watch ME [--until 18:00Z]          block and print your lines as they land, across midnight
swarmdesk.py state ME < notes.md                overwrite your state; state --all shows every state's age
swarmdesk.py decide "text"                      the manager's decision log
swarmdesk.py handover ID new|append < notes.md  handovers, append-only after creation
swarmdesk.py init | roster [add] | doctor
```

## Limits

- **One shared folder.** All sessions must see the same board folder: one machine, or a network mount where file
  locks work. A folder synced between machines by a cloud drive is not safe for several writers.
- **No daemon.** Nothing pushes messages; sessions run `hear` on a cadence (or `watch` where the harness can keep a
  background process). A harness that ends its turn after every reply needs a reminder to keep hearing.
- **Trust.** The board assumes cooperating sessions. It refuses careless mistakes; it does not stop a session that
  edits files by hand.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 examples/make_demo.py      # rebuild the demo board
```

MIT licensed. See [`CHANGELOG.md`](CHANGELOG.md).
