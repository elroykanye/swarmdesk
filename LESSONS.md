# Lessons

Each rule in PROTOCOL.md exists because something went wrong without it. These come from running one manager
session with six to seven worker sessions (two different AI vendors) on a production software team for two
sprints. They are written without the project's names; the mechanics are what matter.

| What happened | The rule it produced |
|---|---|
| A go-ahead was addressed to two sessions on one line. Each reader matched only its own ID, so neither saw it, and both kept asking for a go they already had, for over an hour. | One recipient per line; `say` refuses `A,B`. |
| The manager's watch kept tailing yesterday's channel file after midnight and missed fifty lines. | One file per UTC day; `hear` reads yesterday and today; `watch` follows the day across midnight. |
| Sessions wrote times like "14:1x" that read as clock readings and were not. | The clock stamps every line; hand-written times are refused. |
| Ledger times estimated between turns ran up to two hours ahead of the real clock. | Time comes from the clock, never from memory or estimate. |
| "All 31 documents" was generalised from two samples and was wrong on eight. | Never invent a number; counts come from the whole set, with source and time. |
| Two sessions bumped the same repository to the same version on parallel branches. | CLAIM before a bump, with the version read at that moment; whoever lands second re-bumps. |
| Parallel pull requests in one repository kept colliding on versions and reviews. | One branch and one open change per repository; further verified work goes into the open one. |
| A pull request grew from three commits to twelve after its link was shared, and was merged on a red build. | New commits after a review need a new review and a green build first. |
| A reviewer passed a change, then withdrew the pass when another session found a counterexample on a later commit. | A PASS covers an exact head and nothing else. |
| A session believed a fix was on its branch when it was not. | Quote the exact head in every claim. |
| The manager did the work of a session that had gone quiet, and the session came back to a changed tree. | Silent is not abandoned: the manager asks the human to wake the session, never takes its work. |
| Two writers in one working copy lost each other's changes. | Never commit in another session's working copy. |
| Sessions asked the human for approvals the manager had already given; the human answered the same thing several times. | Every approval is an ASK to the manager; the manager's yes is the human's yes. |
| A permission check refused a command the manager had approved, and the session told the human it "needs your permission". | A harness refusal is BLOCKED to the manager with the exact command, never an approval the human owes. |
| The manager raised a popup for every ticket it moved to review, and the human called it too slow. | The manager approves routine moves itself after checking the evidence. |
| Long status essays flooded the manager. | Five lines to the manager; detail goes in a file. |
| "No change" status lines every fifteen minutes cost tokens and buried real news. | STATUS only when something moved; DONE-FOR-NOW once when idle. |
| Sessions were told to stop for the night while unblocked work waited. | No session idles with unblocked work; saving tokens means short messages, not stopping. |
| Tickets were parked as "waiting on a person" when the answer was already in the ticket history. | Not blocked until proven: show what you searched first. |
| A test job that never started was nearly counted as a result. | NOT RUN is never a pass; a runner reports command, commit, counts and log path. |
| Reviewer verdicts and bot findings sat unread because the inbox tool missed them. | The manager sweeps every review channel each round. |
| A question about a new finding went to the human instead of being delegated. | Findings go to the manager for delegation. |
| A secret was printed by an exception in a read-only check. | `say` refuses lines that look like credentials; `doctor` scans the channel for them. |
| A manager lost its working context to compaction mid-run. | Handover before compaction, appended to and never rewritten. |
| A role moved from one AI vendor's session to another's mid-sprint. | Handovers carry everything not already in the board; the incoming session announces itself. |
| The same decision was argued again a day later because nobody could find it. | The decision log: one clock-stamped line per decision, mistakes included. |
