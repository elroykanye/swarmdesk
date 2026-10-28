# Profile: software team

For a team with code review, continuous integration and shared environments, where AI sessions work alongside
people who merge and deploy. Drawn from a team that ran one manager and seven sessions over two sprints; edit the
names and numbers to yours.

## Merging and review

- Sessions never merge. A named person merges: `<merger>`. The manager sends that person one list of ready changes
  (repository, branch, exact head, version, test result), never a link per change.
- A change is ready when: a reviewer PASS covers its exact head, its build is green, its branch is level with the
  main branch (zero commits behind), and its version is the main branch's version plus one patch.
- One branch and one open pull request per repository per session. Further verified work goes into the open pull
  request; no second one, no second version bump.
- Commits added after a pull request was shared go to the manager with the new head and a green build before
  anyone is asked to merge.
- An AI review is a gate before the person's review, not a replacement for it.

## Versions and commits

- Read the version from the main branch at the moment you bump, and CLAIM it to ALL with that reading.
- Whoever merges second re-reads the main branch and re-bumps.
- Commit messages: `<TICKET>: <imperative summary>`, under 72 characters, no AI attribution trailer.

## Needs the manager's yes

- Any write to shared environments: databases, caches, clusters, message brokers, identity, secret stores, GitOps
  syncs, workflow-tool imports. Read-only checks are fine.
- Every job on a shared cluster, even read-only.
- Opening a pull request, posting to the team's pull-request channel, rerunning a review bot.
- Any ticket comment, transition or new ticket; any message to a person. Draft it in `reviews/` first.
  Ticket descriptions and acceptance criteria are never edited; amendments go in a comment.

## Tickets

- A ticket moves to review only when its evidence exists: a receipt, the deployed version, the live check.
- Every move to review carries a comment asking the reviewer to re-review, mentioning them properly.
- Comments stay under `<word cap>` words; detail goes in the receipt.
- Every ticket mention says in plain words what the change does for the user, not only its key.

## Where tests run

- Targeted unit tests may run on the developer's machine through `<local runner wrapper>` (one run at a time,
  capped CPU and memory). Full suites, browsers, mutation testing and image builds go to the runner.
- No runs on shared environments during `<nightly windows, UTC>`.

## Reaching the human

The manager keeps `for-human.md` and uses its own window's prompt. The human answers there only.
