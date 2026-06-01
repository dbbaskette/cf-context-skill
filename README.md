# cf-context skill

A portable agent skill (Claude Code + Cursor) that makes an AI assistant pick the
right **Cloud Foundry / Tanzu foundation** before it runs any CF command — using
the [`cfctx`](https://github.com/dbbaskette/cfctx) per-shell context switcher.

## What it does

Before any `cf` / `om` / `bosh` / `credhub` command, if no foundation has been
chosen yet this session, the assistant:

1. **Lists** your foundations (`zsh -ic 'cfctx ls'`) and shows the names + API URLs.
2. **Asks** which one to target — it never auto-picks (prod especially must be explicit).
3. **Switches** to it with `cfctx`, and **remembers** the choice for the session.
4. Runs every CF command in that context — `zsh -ic 'cfctx <chosen> && cf …'` — so
   the per-shell `CF_HOME` actually applies even though each command runs in a
   fresh shell.

It only re-asks if you say "switch foundation" / "change context", or a command
fails with an auth/target error.

## Why `zsh -ic`?

`cfctx` is an interactive **shell function** that sets `CF_HOME` (and sources the
per-context `OM_*` / `BOSH_*` / `CREDHUB_*` env) in the **current shell only**.
Agent tool calls each run in a fresh, non-interactive shell where the function
isn't defined — so the skill always invokes it via `zsh -ic '…'` and re-asserts
the context in the same command as the CF call. First switch logs in; the rest
are sub-second (tokens cached).

## Requirements

- [`cfctx`](https://github.com/dbbaskette/cfctx) installed and configured (your
  foundations show up under `cfctx ls`).
- `zsh` as the interactive shell with `cfctx` loaded (its installer adds this).

## Install

```bash
./install.sh
```

This copies the skill into both global skill directories:

- **Claude Code** → `~/.claude/skills/cf-context/`
- **Cursor** → `~/.cursor/skills-cursor/cf-context/`

Then start a fresh session and ask for something like `cf apps` — the assistant
will ask which foundation first.

### Manual install

Copy the `cf-context/` directory into whichever you use:

```bash
cp -r cf-context ~/.claude/skills/         # Claude Code (global)
cp -r cf-context ~/.cursor/skills-cursor/  # Cursor (global)
# or, per-project Cursor rule:
cp -r cf-context <project>/.cursor/rules/
```

## Files

| Path | Purpose |
|------|---------|
| `cf-context/SKILL.md` | The skill (name + description front-matter + instructions) |
| `install.sh` | Installs to the Claude Code and Cursor global skill dirs |
