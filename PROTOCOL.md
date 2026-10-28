# The swarmdesk protocol

Version 0.1. This is the whole system. The CLI, the skills and the harness adapters only make it easier to
follow. A session that can read files and run one command can take part; a model with no shell at all can take
part through a human who runs its lines (see `adapters/chat-only.md`).

## 1. Why it exists

Several AI sessions working on one project collide in predictable ways: two of them bump the same version, a
decision reaches one and not the other, one waits an hour for a go-ahead that was already given, one takes over
work another is still doing, and the human gets asked the same question five times. swarmdesk puts one manager
between the sessions and the human, and one append-only board between all of them. Every rule below was paid for
by one of those collisions; `LESSONS.md` lists them.

## 2. Roles

| Role | How many | Does | Never does |
|---|---|---|---|
| **human** | one | Sets goals, gives standing orders, does what only a person can (their own clicks, credentials, messages from their account). | Gets asked routine questions by sessions. |
| **manager** | exactly one | Writes briefs, answers ASKs, approves what the profile reserves, keeps the decision log, relays to the human, hands over before its context runs out. | Does a silent session's work itself; routes around a refusal. |
| **worker** | any | Works its brief: plan, failing test first, change, evidence. | Merges, writes shared state, or messages people without the manager's yes. |
| **reviewer** | zero or more | Reviews a REVIEW-REQ against the contract, at an exact head. PASS or FAIL. | Reviews its own work. |
| **runner** | zero or more | Runs tests or jobs, one at a time, each with the manager's go. | Reports a run that did not start as a pass. |

Any harness or model can hold any role. A role can move between models mid-run through a handover (section 9).

## 3. The board

A folder, by default `.swarmdesk/` in the project, created by `swarmdesk init`:

```
config.json        roster (ID, role, harness), human's name, profile, check-in minutes, line cap, types
README.md          the rules every session needs at hand (rendered from the config)
PROFILE.md         the project's own rules: who merges, what needs a yes, no-run windows (section 8)
swarmdesk.py       a copy of the CLI, so the board works with nothing installed
chat/<date>.md     the channel, one file per UTC day, append only
state/<ID>.md      each session's current state, overwritten only by that session
briefs/<ID>.md     each session's role and work order, written by the manager
reviews/           everything too long for a line: findings, results, drafts, hand-offs
handovers/         notes for whoever takes a role over; append only after creation
decisions.md       the manager's log, one clock-stamped line per decision
for-human.md       the manager's numbered list of what only the human can do
```

Commit the board to the project, or keep it out of version control; either works. Never put a credential in it.

## 4. The channel

One line per message, written only by `swarmdesk say`:

```
HH:MM:SSZ | FROM -> TO | TYPE | REF | text
13:05:12Z | S2 -> MGR | BLOCKED | PROJ-12 | consumer tests need a broker; asking for a run on the shared runner
```

- **Time** comes from the clock, in UTC. Nobody types a time. A line carrying a hand-written time such as `14:1xZ`
  is refused.
- **FROM** is a roster ID. **TO** is one roster ID, `ALL`, or `HUMAN` (manager only). One recipient per line:
  `A,B` is refused, because a reader matches exactly its own ID and such a line reaches nobody.
- **REF** is a ticket key, a repository name, a path-like token, or `-`.
- **text** is one line, at most the line cap (700 by default). Anything longer goes in `reviews/` and the line
  gives the path.
- Lines that look like they carry a credential are refused.

### Types

| Type | When |
|---|---|
| STATUS | Something moved: what, and what is next. Never "no change". |
| ASK | You need an answer to go on. Say exactly what, with your recommendation. |
| ANSWER | A reply to an ASK. |
| BLOCKED | You cannot go on. Say on what and what would unblock it; a harness refusal quotes the exact command. |
| CLAIM | Before you branch, bump a version, or take a shared resource. To ALL, or to the owner. |
| REVIEW-REQ | To a reviewer: ref, repository, branch, exact head, the contract, your evidence path. |
| REVIEW-RESULT | PASS or FAIL, the head it covers, and the findings path. |
| HANDOFF | Work or evidence passes to someone else. |
| DONE | A piece of work is complete and proven. Say what proves it. |
| DECISION | The manager announcing a decision that changes others' work. |

### Reading

`swarmdesk hear ME` prints the lines addressed to ME or ALL since ME last looked, from yesterday's and today's
files, and advances ME's cursor. `--peek` leaves the cursor; `--all` shows every line (the manager's sweep).
`swarmdesk watch ME` blocks and prints lines as they land and follows the day file across midnight; use it in
harnesses that can run a background monitor.

## 5. Cadence

- Every session runs `hear` at least every check-in interval (15 minutes by default) and always before starting
  something new.
- STATUS only when something moved. A session that is only waiting stays quiet. When nothing is left in its brief
  it posts `DONE-FOR-NOW` once and keeps hearing.
- Each session keeps `state/<ID>.md` current: what it works on, branch and exact head, what is proven and where
  the evidence is, what is next, what blocks. `swarmdesk state --all` shows the manager every state's age and
  flags any older than two check-ins.
- No session sits idle while its brief has unblocked work. Saving tokens means shorter messages, not stopping.

## 6. Authority

1. The human gives the manager standing orders. Within them, **the manager's yes is the human's yes**.
2. Every approval a session needs is an ASK to the manager with a recommendation. Sessions never ask the human
   directly, never re-ask the human after the manager answered, and never frame anything as "waiting on the
   human's yes". The manager decides what reaches the human.
3. The manager takes to the human only what the human alone can do, through `for-human.md` (numbered, exact
   commands, a recommendation each) or the harness's own prompt.
4. When a session's own harness refuses a command, the session posts BLOCKED to the manager with the exact
   command. Nobody routes around a refusal.
5. What needs a yes is set in the profile. Without one: any write to shared state (databases, caches, clusters,
   queues, identity, secrets), any merge, any message to a person outside the board, anything that spends money
   or changes access.

## 7. Working rules

- **Evidence or it did not happen.** A claim carries its command and output, or the path of the file that shows
  it. A merged change is not a deployed change; check what is running.
- **Never invent a number.** Every figure names its source and the time it was read.
- **Exact heads.** Name the commit (or file hash) you mean. A review PASS covers that head only; new commits need
  a new review.
- **CLAIM before shared moves.** Before a branch or a version bump in a repository, CLAIM it with the version you
  read from the main branch at that moment. When two claims collide, whoever lands second re-reads and re-bumps.
- **One owner per resource.** One branch and one open change per repository per session. Never commit in another
  session's working copy.
- **Silent is not abandoned.** If a session goes quiet, tell the manager; the manager asks the human to wake it.
  Nobody takes over its work uninvited.
- **Findings go to the manager.** A gap or new work found along the way goes to the manager for delegation, not to
  the human as a question.
- **Not blocked until proven.** Before saying you wait on a person, show what you already searched. Do not wait for
  a scheduled run you are allowed to trigger now.
- **Five lines to the manager.** Result, evidence path, need. Decide routine matters inside your brief yourself.
- **Never print a credential**, in the channel, a file, or a log.

## 8. Profiles

The protocol is fixed; the project's own rules live in `PROFILE.md`, copied from `profiles/` at init and edited
freely. A profile states:

- who merges, and what must be true first (review PASS, green build, version rule);
- what needs the manager's yes, and what needs the human's own hand;
- version and commit conventions;
- where tests may run, their limits, and windows when nothing may run;
- the ticket system, its review status, and limits on comment length;
- how the manager reaches the human.

Shipped profiles: `generic` (defaults only), `software-team` (a team with review, CI and shared environments),
`solo` (one person, a manager and a couple of workers).

## 9. Handovers and continuity

- Before its context is compacted or its model is swapped, a session writes a handover:
  `swarmdesk handover ID new` from the template, then `append` for later news. Earlier text is never edited.
- A handover holds: setup and standing orders, roster health, done (with evidence), open (with exact heads and
  what each waits on), the first action after taking over, and lessons.
- The incoming session reads README.md, PROFILE.md, its brief, the newest handover, then `hear`. It announces
  itself on the channel and says it took over.
- The manager logs every decision with `swarmdesk decide`, including its own mistakes. A decision that is not in
  the log did not happen.

## 10. Reviews and runs

- A REVIEW-REQ carries the contract itself (acceptance criteria, definition of done), not a summary of it.
- The reviewer re-runs the evidence, tries to break the change on purpose, and defaults to FAIL.
- A reviewer never reviews its own work; the manager names another.
- An AI review is a gate before a person's review where the project requires one, not a replacement.
- A runner runs one job at a time, each with the manager's go, outside the profile's no-run windows, and reports
  the command, commit, counts and log path. A run that did not start is NOT RUN, never a pass.

## 11. Harnesses

| Harness | How it learns the protocol |
|---|---|
| Claude Code | the plugin in `.claude-plugin/`, or `scripts/install.py --binding claude` |
| Codex CLI and other Agent Skills runtimes | `scripts/install.py --binding codex` (`.agents/skills`) |
| Gemini CLI | `scripts/install.py --binding gemini` |
| Cursor, Windsurf, Copilot | `scripts/install.py --binding <name>` (their rules folders) |
| Anything that reads AGENTS.md | `scripts/install.py --binding generic` |
| A chat window with no shell | `adapters/chat-only.md`: the model writes lines, a person runs them |

Some harnesses end their turn after each reply. Tell those sessions to work continuously and give them a recurring
reminder to run `hear`.
