# Profile: solo

One person, one manager session and two or three workers, often on one machine.

## Needs the manager's yes

- Pushing to a remote, merging, deleting branches.
- Installing packages globally, or anything outside the project folder.
- Anything that costs money (paid APIs, cloud resources).

## Needs the human's own hand

- Credentials and account settings.

## Conventions

- Each worker uses its own git worktree; nobody commits in another's.
- Heavy commands (full builds, large test suites) run one at a time; the manager orders them.

## Reaching the human

The manager asks in its own window. The human checks `for-human.md` when they come back.
