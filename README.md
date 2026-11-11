# cf-context skill

An agent skill for selecting and checking an explicitly intended Cloud Foundry /
Tanzu foundation with [nkuhn-vmw/cfctx](https://github.com/nkuhn-vmw/cfctx).
Works with agents that load `SKILL.md` directories, including Codex, Claude Code,
and Cursor.

## Behavior

- Uses a foundation named by the user or already confirmed for the task; asks
  only when the target is absent or ambiguous.
- Prefers upstream `cfctx-env` for noninteractive execution, avoiding interactive
  shell startup and automatic login/enrichment on each command.
- Loads the context in each invocation, clears inherited platform variables,
  stops on load failures, and verifies cached CF API/org/space fields.
- Preserves literal command arguments and child exit status. Recovery is bounded
  and never silently switches foundations or replays uncertain mutations.
- Keeps credential-bearing exports and CF config out of normal inspection output.

The helper checks local configuration, not live authentication, user authority,
remote server identity, or arbitrary command overrides. The skill supplies the
additional decision rules. Context files must be trusted local shell files.
Shared per-context caches are not isolated between concurrent commands.

## Requirements

For the normal path: Bash, `jq`, `cfctx-env` on PATH, configured private
`context.env` files (mode 600 or 400), and the requested platform CLI. CF commands
also need a cached configuration whose target agrees with the context.

`cfctx-env` is provided by upstream cfctx; the separate `cfctx-run` workspace
runner is optional. Recovery, older shell-only installations, and provisioned
workspace credentials are documented in the skill's runtime reference.

## Install

```bash
./install.sh
```

Copies the complete skill into `~/.claude/skills/cf-context/` and
`~/.cursor/skills-cursor/cf-context/`. Re-run to update. For Codex or another
skill-directory host, copy the complete `cf-context/` folder into its skill root;
for example:

```bash
mkdir -p ~/.codex/skills
cp -R cf-context ~/.codex/skills/
```

Start a fresh agent session after installation. Example request:
"Use cdc and list the apps in my confirmed org/space."

## Verification

No real credentials, platform CLI installation, or foundation access is needed:

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh cf-context/scripts/context.sh scripts/ci/guest-test.sh
```

Tests cover failure-before-execution, inherited state, target mismatches, argument
quoting, secret-free inspection, exit status, and complete/idempotent installation
in disposable homes. Set `CF_CONTEXT_TEST_UPSTREAM` to a reviewed local copy of
upstream `bin/cfctx-env` to repeat the same tests against that implementation.
This checks compatibility without vendoring upstream or contacting a foundation.

For the existing shared macOS Tart runner, use `scripts/ci/guest-test.sh` as the
guest entry point; it runs the full suite in a disposable clone and retains logs.
The runner is development infrastructure, not a skill runtime dependency.

## Files

| Path | Purpose |
|---|---|
| `cf-context/SKILL.md` | Target selection, execution, recovery, and completion rules |
| `cf-context/scripts/context.sh` | Checked inspection and command execution |
| `cf-context/references/runtime.md` | Conditional procedures and pinned upstream evidence |
| `tests/test_context.py` | Offline behavioral and installer regression tests |
| `scripts/ci/guest-test.sh` | Full-suite entry point for the shared Tart runner |
| `install.sh` | Installs the complete skill for Claude Code and Cursor |
