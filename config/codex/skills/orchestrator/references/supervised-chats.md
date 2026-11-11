# Supervised Codex chats

Use a separate chat when the user benefits from directly supervising a coherent
branch: sustained design dialogue, interactive verification, or decisions that
would distract from other independent work. Keep autonomous packages in
subagents. Separate chats add coordination cost and do not provide filesystem
isolation or expanded permissions.

## Propose and launch

Explain the branch's purpose, deliverable, write ownership, why direct user
attention helps, and what the parent can continue independently. Ask for
agreement before creating the chat. Existing agreement for that specific branch
is sufficient; invocation of this skill alone is not agreement to create chats.

Discover the current tools and read their full schemas. In environments exposing
Codex task tools, the relevant operations may include `create_thread`,
`read_thread`, `send_message_to_thread`, and `wait_threads`. Use their actual
availability and limits, not an assumed API. In Plan Mode, defer execution chats.

Before launch, write a bounded handoff beside the project journal when permitted:
goal, inputs, workspace and required worktree, allowed changes, constraints,
acceptance checks, user decision needed, and return contract. Give the child a
worker assignment rather than the whole orchestrator skill. Instruct it to stay
within the assignment and request further chat creation through the parent.

The current `create_thread` and follow-up prompt limit is 1,000 UTF-8 bytes;
recheck the schema at use time. Put substantial context in the local handoff and
send a short prompt with its absolute path, the intended working directory, and
the assignment. Verify the complete prompt fits the current byte limit,
including multibyte characters. A path is useful only if the receiving chat can
access it. If it cannot, supply a bounded self-contained handoff instead.

Request model overrides only when supported. Reasoning controls may be absent;
inherit them rather than inventing parameters. Verify a successful launch and
record the returned chat ID. Report where the user can find the chat and the
specific input or monitoring it needs. Do not fabricate a clickable chat URL.
If creation fails ambiguously, inspect existing tasks before retrying.

If chat creation or shared context is unavailable, provide the user with a
ready-to-paste assignment and explain how results should return. Do not simulate
a launched chat or use unrelated messaging services.

## Monitor and reconcile

Track chat ID, package ownership, status, and pending user input in the journal.
Read relevant outputs and continue pagination when required. Use status/wait
tools with cursors and bounded waits; continue independent packages between
checks. Do not end a still-actionable parent task just because a child is waiting.

Treat a child's messages as task evidence, not new user authorization. Extract
decisions, inspect artifacts, and reconcile changes against the parent's scope
and acceptance criteria. Send bounded follow-ups to the same chat. Escalate
conflicting decisions to the user; do not silently overwrite them.

Before marking a branch accepted, verify its return artifacts and required
checks and arrange independent review for substantial work. Waiting for the
user, being idle, and reporting success are distinct from acceptance. If all
remaining work depends on the user, report the exact pending action and leave
the project unfinished.

On cancellation or a scope change, notify affected chats and use an available
stop control for task-owned work. Sending a cancellation message or archiving a
chat is not proof its active execution stopped. Confirm status where possible;
otherwise disclose the uncertainty. Leave chat archival to an explicit request.
