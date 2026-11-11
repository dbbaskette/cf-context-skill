![cf-context — a playful switchboard connecting to the selected cloud foundation](assets/cf-context-header.png)

# cf-context

**Help your AI assistant run Cloud Foundry commands against the foundation you intended.**

If you work with more than one Cloud Foundry environment, “list my apps” leaves
an important question unanswered: *which one?* This skill teaches your assistant
to use the foundation you name, ask when the target is unclear, and check the
context before running a command.

> “Use cdc and show me the current CF target, including the org and space.”

The assistant loads `cdc`, checks its configured target, and runs `cf target`.
It remembers your choice for the task and reloads that context for subsequent
commands—even when each tool call starts a fresh shell.

## What you’re installing

A **foundation** is a Cloud Foundry installation, such as your development,
staging, or production environment. A **context** is its saved local configuration.

| Component | Its job |
|---|---|
| [cfctx](https://github.com/nkuhn-vmw/cfctx) | Stores and switches your foundation contexts; supplies the `cfctx-env` command. |
| **This skill** | Teaches an AI assistant how to choose a context, verify it, and handle failures. Includes a small helper for repeatable checks. |
| Your platform CLI | Runs the actual command: `cf`, `om`, `bosh`, or `credhub`. |

This repository installs the skill. Set up `cfctx` and your platform CLI first.

## Get started

### 1. Check your prerequisites

You need:

- An agent that supports `SKILL.md` skills, such as Codex, Claude Code, or Cursor.
- [cfctx installed and configured](https://github.com/nkuhn-vmw/cfctx#install), with `cfctx-env` available on your agent’s `PATH`.
- Bash, [`jq`](https://jqlang.org/download/), and the platform CLI you want to use.
- An existing context with a private `context.env` file and, for CF commands, a matching cached CF target.

In your terminal, list your configured foundations:

```bash
cfctx-env --list
```

For example, you might see:

```text
cdc
ndc
```

If the list is empty, configure a context using the
[cfctx setup guide](https://github.com/nkuhn-vmw/cfctx) before continuing. If you
need to establish a CF login, select that context in your configured interactive
terminal:

```bash
cfctx cdc
```

Replace `cdc` throughout this guide with a name from **your** list. Complete any
required sign-in in your terminal. The skill reuses the saved configuration and
tokens; installing it does not create a new account or log you in.

### 2. Download the skill

```bash
git clone https://github.com/dbbaskette/cf-context-skill.git
cd cf-context-skill
```

### 3. Install for your agent

**Codex**

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/cf-context"
cp -R cf-context/. "${CODEX_HOME:-$HOME/.codex}/skills/cf-context/"
```

**Claude Code and Cursor**

```bash
./install.sh
```

The installer copies the skill into both of these locations:

- Claude Code: `~/.claude/skills/cf-context/`
- Cursor: `~/.cursor/skills-cursor/cf-context/`

To install for just one of them, use the corresponding command pair instead:

```bash
# Claude Code only
mkdir -p ~/.claude/skills/cf-context
cp -R cf-context/. ~/.claude/skills/cf-context/

# Cursor only
mkdir -p ~/.cursor/skills-cursor/cf-context
cp -R cf-context/. ~/.cursor/skills-cursor/cf-context/
```

For other agents, copy the **entire `cf-context/` folder** into their documented
skill directory. The helper and reference files are required alongside `SKILL.md`.

### 4. Try your first request

Start a fresh agent session, then ask:

> Use foundation cdc. Show me the current CF target, including the org and space.

Once the reported target is the one you want:

> List the apps in that org and space.

You should see the selected foundation and the command result. If you omit the
foundation and haven’t chosen one for the task, the assistant should show the
available names and ask which to use. It should not guess—even if only one exists.

## Everyday examples

| Ask your assistant | Expected behavior |
|---|---|
| “Use cdc and list the apps in my confirmed org and space.” | Uses the named foundation without asking you to select it again. |
| “Show the services in the same space.” | Reuses your choice and loads its context for the new command. |
| “Switch to ndc and show the current CF target.” | Checks the newly named context and uses it for subsequent commands. |
| “Use cdc and list BOSH VMs.” | Loads that context’s BOSH settings before running `bosh vms`. |
| “What does `cf push --help` say?” | Shows local help without requiring a foundation. |

Choosing a foundation does not grant permission to deploy or delete anything.
The assistant follows the authority in your actual request.

## What happens before a command?

1. **Choose:** use your explicit foundation or the one you already confirmed.
2. **Load:** use `cfctx-env` in the same invocation as the command, clearing
   inherited platform variables so settings from another context do not carry over.
3. **Check:** reject failed loads and CF API/org/space mismatches before running
   the requested CF command.
4. **Run:** preserve the command’s arguments and exit status, then report the result.

The normal path avoids interactive shell startup and repeated login or enrichment.
Authentication recovery is bounded, and an uncertain deployment or other mutation
is not automatically repeated.

The checks verify local configuration. They do not prove that a token is accepted
by the server, verify every remote server’s identity, or replace platform access
controls. Context files are trusted local shell code, and per-context caches are
shared: avoid simultaneous retargeting or login against the same context.

## If something gets stuck

| What you see | What to check |
|---|---|
| `cfctx-env` not found | Confirm cfctx is installed and its helper is on the **agent’s** `PATH`, not just your terminal’s. |
| No contexts listed | Configure a context in cfctx first. The skill does not create one from a guessed name. |
| Missing or unreadable `context.env` | Check the selected context’s setup. Its env file must have private permissions: mode `600` or `400`. |
| Cached CF API/org/space differs from the context | Resolve the intended target. The assistant stops rather than silently retargeting or changing saved defaults. |
| Expired login or SSO required | Keep the same foundation and complete the indicated sign-in. Human SSO belongs in your terminal, not in chat. |
| Connection, DNS, or TLS error | Check the reported error and your network/VPN access. The skill does not keep retrying or disable certificate checks. |
| The agent does not discover the skill | Check the installation directory and start a fresh session. Confirm that the complete folder was copied. |

For detailed recovery, older shell-only installations, or an already provisioned
`cfctx-run` workspace, see the [runtime guide](cf-context/references/runtime.md).
Do not paste raw context exports, CF config files, or credentials into chat.

## Update

From this repository’s directory:

```bash
git pull --ff-only
```

Repeat the installation commands for your agent, then start a fresh session.
Installed copies do not automatically track this checkout.

## For contributors

The tests use disposable homes, synthetic contexts, and fake platform CLIs.
They need Python 3, Bash, and `jq`; no real credentials or foundation access.

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh cf-context/scripts/context.sh scripts/ci/guest-test.sh
```

Coverage includes failed loads, stale environment variables, target mismatches,
argument quoting, inspection output, exit status, and complete/idempotent installs.
To check upstream compatibility, set `CF_CONTEXT_TEST_UPSTREAM` to a reviewed
local copy of upstream `bin/cfctx-env` and run the same suite.

| File | Purpose |
|---|---|
| [SKILL.md](cf-context/SKILL.md) | The assistant’s target-selection and execution instructions |
| [context.sh](cf-context/scripts/context.sh) | Checked context inspection and command execution |
| [runtime.md](cf-context/references/runtime.md) | Recovery procedures and pinned upstream references |
| [test_context.py](tests/test_context.py) | Offline regression tests |
| [guest-test.sh](scripts/ci/guest-test.sh) | Entry point for the shared macOS Tart test runner |
| [install.sh](install.sh) | Complete-skill installer for Claude Code and Cursor |
