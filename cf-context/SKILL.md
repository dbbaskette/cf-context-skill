---
name: cf-context
description: >
  Select and switch the active Cloud Foundry / Tanzu foundation with the `cfctx`
  tool BEFORE running any Cloud Foundry command. Trigger this whenever you are
  about to run a `cf` command (cf push, cf apps, cf login, cf target, cf logs,
  cf services, cf ssh, cf env, cf restage, …) or an `om` / `bosh` / `credhub`
  command, and a foundation has not been chosen yet in this session. Ask the user
  which foundation to target (showing the options), switch to it, then run their
  command in that context. Also trigger when the user says "switch foundation",
  "change CF context", "use the prod/ndc/cdc foundation", etc.
---

# Cloud Foundry Context (cfctx)

`cfctx` is a per-shell Cloud Foundry / Tanzu **foundation switcher** (think
`kubectx`, for CF). It points the current shell at a foundation — sourcing that
context's `OM_*` / `BOSH_*` / `CREDHUB_*` env and running `cf login` — and caches
tokens so later switches are sub-second.

## When this applies

Before running **any** of these, a foundation must be selected:
`cf …`, `om …`, `bosh …`, `credhub …`.

## The rule — ask once per session, then reuse

### 1. If no foundation has been chosen yet this session

**a. List the foundations.** `cfctx` is a shell function only available in an
interactive shell, so always invoke it via `zsh -ic`:

```bash
zsh -ic 'cfctx ls'
```

Output (ignore the shell's prompt/persona banner line, e.g. `🤖 …`):

```
  cdc [env]  https://api.sys.tas-cdc.kuhn-labs.com
  ndc [env]  https://api.sys.tas-ndc.kuhn-labs.com
```

The **first token** on each line is the foundation name (`cdc`, `ndc`, …).

**b. Ask the user which one** to target — show the names and their API URLs. Use
`AskUserQuestion` if you have it; otherwise ask plainly and wait for the answer.
**Never choose for them** — production targets especially must be explicit.

**c. Remember the chosen name** for the rest of this conversation (e.g. `cdc`).

### 2. Run every CF command in the chosen context

`cfctx` only affects the shell it runs in, and each tool call is a fresh shell —
so re-assert the context **in the same invocation** as the command:

```bash
zsh -ic 'cfctx <chosen> && cf <args>'
# examples:
zsh -ic 'cfctx cdc && cf apps'
zsh -ic 'cfctx cdc && cf push -f manifest.yml'
```

The first `cfctx <chosen>` of the session may take a few seconds (it logs in);
every one after is instant (tokens cached). For the same reason, prefix `om` /
`bosh` / `credhub` commands the same way: `zsh -ic 'cfctx <chosen> && bosh vms'`.

If a command's arguments contain single quotes, write the command to a temp
script and run `zsh -ic 'cfctx <chosen> && bash /tmp/cmd.sh'` instead of fighting
the quoting.

### 3. Do not ask again

Once chosen, reuse that foundation for every CF command for the rest of the
session **without re-asking** — unless:
- the user explicitly asks to switch ("use ndc", "change context", "switch
  foundation"), or
- a command fails because the context was lost or the login expired.

### Reading cfctx's switch output

On switch, `cfctx` prints what happened — interpret it before assuming success:
- **`✓ cf logged in`** → good, proceed.
- **`token expired … Please log back in`** (from the `cf` command) → the cached
  token lapsed. Re-assert `cfctx <chosen>` once (it re-authenticates); then retry.
- **`cf api failed — check CF_API and network`** / `cf apps` failing right after,
  with the foundation **unreachable** → the foundation is down or needs VPN. Do
  **not** loop retrying — tell the user plainly (e.g. "cdc looks unreachable —
  VPN connected?") and offer to target a different foundation instead. A quick
  `curl -sk -o /dev/null -w '%{http_code}' --max-time 8 <api-url>` confirms
  reachability (`000` = unreachable).

## Guardrails

- **Always go through `cfctx`.** Never run `cf api` / `cf login` directly to aim
  at a foundation — that skips the per-context `OM_*` / `BOSH_*` / `CREDHUB_*`
  env `cfctx` sets up.
- **Invoke via `zsh -ic '…'`.** A plain `bash`/non-interactive shell won't have
  the `cfctx` function.
- Ignore the interactive shell's prompt/persona banner line in the output.
