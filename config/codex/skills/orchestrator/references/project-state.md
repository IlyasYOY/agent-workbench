# Project state

For a substantial task, maintain `_orchestration/<task-slug>/state.md` under the
current workspace, unless applicable instructions designate another location.
Inspect existing state first. Reuse the matching task, and choose a distinct
slug for unrelated work. Create notes only when writing is allowed. Keep them
out of commits unless the user asks to include them; preserve existing files
without changing ignore rules merely to hide the journal.

The journal is a compact recovery record, not a transcript. Record:

- Goal, acceptance criteria, boundaries, and active orchestration mode.
- Decisions, assumptions, and user authorizations relevant to the work.
- Work packages: ID, deliverable, status, dependencies, owner, write scope,
  repository/worktree, worker or chat ID, artifact pointers, and review state.
- Checks: command, working directory, revision or artifact tested, result, and
  evidence location; distinguish passed, failed, and not run.
- Blockers, pending user decisions, attention needed in other chats, and next
  ready actions.

Update on dispatch, material decisions, accepted results, blockers, handoff, and
completion. Keep the parent as journal owner; workers return updates rather
than racing to rewrite shared state. Store supporting artifacts beside the
journal only when useful. Use source pointers instead of copying large logs,
chat histories, or secrets.

## Recover or hand off

After compaction or continuation, read the matching journal and applicable
instructions, then verify current repository/artifact state and recorded worker
or chat status through available tools. Notes are evidence to check, not an
authority that overrides current user instructions. Resolve stale assignments
before restarting work so an old writer is not duplicated.

Resume the next ready package; ask only about unresolved intent or authorization.
When starting a genuinely new chat, provide the journal path and explicitly
request `$orchestrator` if that chat should also coordinate work. A journal
records the previous mode; it does not independently activate a skill in a new
chat. A bounded worker chat usually needs its assignment, not the parent role.

If journal writes are unavailable, keep a compact state summary in the chat and
include it in handoffs. Do not claim a durable checkpoint was saved.
