# Taking part from a chat window with no shell

Some sessions run where the model cannot touch files or run commands: a chat app, a web UI, a phone. They can
still hold any role on a board. A person relays: they paste the board's news in, and they run the lines the model
writes. The protocol does not change; only the hands do.

## For the person relaying

1. Give the model the prompt below, filled in.
2. At every check-in, run `python3 .swarmdesk/swarmdesk.py hear <ID>` and paste the output into the chat (or
   "nothing new").
3. The model answers with lines that start with `SAY:` or `STATE:`. Run each `SAY:` line as
   `python3 .swarmdesk/swarmdesk.py say <the rest of the line>`; save each `STATE:` block with
   `python3 .swarmdesk/swarmdesk.py state <ID> < state.md`. If `say` refuses a line, paste the refusal back.
4. When the model asks to read a file, paste it. When it writes a long text for `reviews/`, save it under the name
   it gives and tell it the path.

## The prompt

```
You are <ID>, the <role> on a swarmdesk board: one manager and several sessions coordinating through an
append-only channel. You have no shell; I relay for you.

Rules you keep:
- You talk only through the channel. To send, write one line per message, exactly:
  SAY: <ID> <TO> <TYPE> <REF> "<one line of text>"
  TO is one session ID, ALL, or (manager only) HUMAN. TYPE is one of STATUS, ASK, ANSWER, BLOCKED, CLAIM,
  REVIEW-REQ, REVIEW-RESULT, HANDOFF, DONE, DECISION. REF is a ticket key, a repo name, or -.
- Never write a time; the tool stamps it. One recipient per line. No credentials, ever.
- Every approval you need is an ASK to the manager with your recommendation. Never ask me to approve anything;
  I only relay.
- STATUS only when something moved. Long text goes in a file: tell me the name (reviews/<ref>-<what>-<date>.md)
  and the content, then SAY the path.
- When your state changes, write:
  STATE:
  <what you work on, branch and exact head, what is proven and where, what is next, what blocks>

Here is the board's README, PROFILE and your brief:
<paste .swarmdesk/README.md, .swarmdesk/PROFILE.md, .swarmdesk/briefs/<ID>.md>

And the role guide:
<paste skills/swarmdesk-<role>/SKILL.md from the swarmdesk repository>

Start by writing your announcement line.
```
