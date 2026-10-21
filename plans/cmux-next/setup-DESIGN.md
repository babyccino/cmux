# `cmux setup`: setup an agent can do

Lawrence: "the chief should be able to just set stuff up." Leo: "nobody reads
the docs except agents." So every setup task gets one entry point an agent
finds and runs, with machine-readable results, and the person is asked only
for what a person must do: an OAuth sign-in, a secret, a macOS switch.

## Inventory (2026-10-21, feat-cmux-next)

| Task | Done today | Agent path today | JSON | Safe to re-run |
| --- | --- | --- | --- | --- |
| cmux sign-in, accounts | GUI (Settings > Accounts, sidebar) | `cmux accounts list` reads; `cmux cloud sign-in` opens the browser; reauth/connect are person-only | yes (list) | list yes; sign-in refuses when signed in |
| Harness install and sign-in | GUI (Settings > Agents, Harnesses page) | `cmux setup harness [ID ...]`; `cmux harness list/doctor/login --json`; install and sign-in are the user's | yes | yes |
| Folder trust | GUI (TrustAsk line, sub-session card) | none: raw `acp.trust.set` over the acpmux socket | - | - |
| Add an ssh machine | GUI (Connect to Machine...) | `cmux acp host setup SSH --json`; `cmux remote connect` | yes (acp) | yes |
| acpmux peers, host updates | none in the app | `cmux acp host ls/update --json` | yes | yes |
| Cloud machine | GUI (New Cloud Machine sheet) | `cmux cloud new-machine` opens the sheet; `cmux-vm create` (operator) | sheet no; cmux-vm yes | cmux-vm yes (idempotency keys) |
| Tailscale, mesh | CLI only | `cmux host enable/status --json`; needs Tailscale signed in | yes | yes |
| MCP servers | docs only | `cmux agents doctor --json` checks cmux-cua; `claude mcp add cmux -- cmux mcp serve` | doctor yes | yes |
| Computer Use | GUI (Computer Use Setup) | `cmux agent computer-use-setup`; grants are switches in System Settings | doctor yes | yes |
| Browser import | GUI (Import from Browser...) | `cmux bookmark import-from-browser`, `cmux browser import-cookies` (consent panel); history and passwords person-only | partly | bookmarks/history merge |
| Keyboard shortcuts | GUI (Keyboard Shortcuts) | `cmux keybinding list/resolve --json`; edits only over the raw socket or keybindings.json | reads yes | yes |
| Notifications | GUI (Settings) | `cmux settings get/set notifications.*`; macOS permission asked on first use | yes | set yes; toggle-workspace-mute no |
| Team invites | web dashboard | `POST /api/teams/<id>/invitations`; `cmux home invite --email` for Home conversations | API yes | no |

There is no onboarding sequence in cmux NEXT (Lawrence, 2026-10-09): the
onboarding window shows one step, browser import or Computer Use, when asked.

## The surface

`cmux setup` is a CLI scope beside `cmux agents`, for agents: every command
prints one JSON object, with or without `--json`.

- `cmux setup list`: every task above as `{id, summary, setup, check, apply,
  person}`. `setup` is the `cmux setup` command when setup runs the task;
  `check` and `apply` are the commands that do it today; `person` is what
  only the person can do. One read gives an agent the whole map, including
  tasks setup does not run yet.
- `cmux setup status`: the read-only check of every task setup runs.
- `cmux setup <task> ... [--dry-run]`: check, then change only what is not
  already right. The result is

  ```json
  {"schema_version": 1, "task": "trust", "state": "changed", "dry_run": false,
   "before": {...}, "after": {...}, "undo": "cmux setup trust /repo --level unknown",
   "user_action": null}
  ```

  `state` is `ok` (nothing to do; nothing written), `changed`, `planned`
  (`--dry-run`), `needs_user` (`user_action` names the one thing the person
  does: `{kind, text, command, url}`) or `failed`. `undo` is the command
  that puts the old state back. Exit 0 unless the task failed (1) or the
  arguments are wrong (2).

Default allow, with undo: an agent runs a task without asking when it stays
on this Mac and has an undo. It asks first only for what reaches outside
(invites, a paid Cloud machine, opening this machine to a new peer).

The Chief loads the `cmux-setup` skill (shipped in optchat-chief's
`BUILTIN`, written to `~/.cmux/chief/skills/`), and its prompt points there.
`cmux docs search setup` and the MCP `cmux_docs` tool find the same map.

## Tasks setup runs

1. `trust [FOLDER] [--level trusted|untrusted|unknown]`.
   It writes acpmux's own record (`acpmux::trust`), the answer the pane's
   Trust question and the trust gate read, through the running daemon when
   there is one so a sub-session waiting on the folder goes on at once.
   Claude Code's and Codex's files keep their one writer. The record already
   holding the level is `ok`; `undo` names the level it held before.
2. `harness [ID ...]`: for each named harness, else every configured or
   discovered one, whether its CLI is installed (its command resolves),
   signed in and outdated. It runs acpmux's health check
   (`acpmux::harness_health`, the rows of `_acpmux/harness/health`) as a
   library, so the answer is fresh and needs no daemon. A sign-in that
   evidence (`auth.check`, the agent's login files) leaves unknown is asked
   of an ACP harness itself, as `cmux harness login ID --status` does
   (`initialize` and `session/new`); `cmux harness doctor` runs a prompt
   turn and stays the deep check. Outdated compares the installed version
   with the newest one the daemon last read (`harness-health.json`), so
   setup asks no registry. A named id that is not configured is checked
   with the profile acpmux ships for it (`configured: false`). The result
   is

   ```json
   {"schema_version": 1, "task": "harness", "state": "needs_user", "dry_run": false,
    "harnesses": [{"id": "gemini", "name": "gemini", "state": "needs_user",
      "configured": true, "installed": true, "program": "/usr/local/bin/gemini",
      "path": "/usr/local/bin/gemini", "version": "0.1.0", "signed_in": false,
      "auth_detail": "session/new failed (-32000): ...", "outdated": false,
      "latest": "0.1.0", "update": null, "problem": null,
      "user_action": {"kind": "oauth", "command": "cmux harness login gemini", ...}}],
    "undo": null, "user_action": {"kind": "oauth", ...}}
   ```

   A harness is `ok` when it is installed and nothing says it is signed
   out (`signed_in` is `null` when cmux cannot see the sign-in, such as
   Claude Code's keychain login; its first chat asks if it must). Signed
   out is `needs_user` with kind `oauth` and `cmux harness login ID`; a
   missing CLI is `needs_user` with kind `install` and the profile's docs
   as `url`. The task state is `needs_user` when any harness is, and its
   `user_action` is the first one. It writes nothing: install and sign-in
   are the person's, and an update has no undo, so an outdated harness
   names its `update` command instead of running it. UniiChat (the bundled
   adapter, offered everywhere) counts only when named or configured; no
   harness at all is `needs_user` to install one.
3. `machine SSH_TARGET` (next): `acp host setup`, and `acp host enroll` once
   #22823 lands (install, daemon, harness, peers both ways, doctor).
