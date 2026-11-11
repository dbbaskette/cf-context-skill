---
name: cf-context
description: Select, load, and verify an explicitly intended Cloud Foundry or Tanzu foundation using cfctx before target-dependent cf, om, bosh, or credhub commands. Use also for requests to switch foundations or diagnose context/authentication failures.
---

# Cloud Foundry context

Use a confirmed foundation in every tool invocation. Remember the user's choice,
not shell state: `CF_HOME` and credentials do not carry between tool calls.
Local `--help` / version commands and editing CF files need no foundation.

If the workspace already supplies a `cfctx-run` descriptor or credential producer,
use [workspace credentials](references/runtime.md#workspace-credentials) instead
of local context discovery below. Do not require local `cfctx-env` for that route.

## 1. Resolve the target

1. Discover once per environment: `command -v cfctx-env`, then
   `cfctx-env --list`. This returns names only, one per line. An empty list
   means there are no configured contexts; stop and report it.
2. Choose in this order: the current request's explicit name; otherwise the
   previously confirmed name for this task and context root; otherwise ask.
   Match an exact listed name. Do not infer from a current-shell marker,
   directory, a sole available context, or words such as "production" without
   an established mapping. A new explicit name supersedes the old one.
3. If ambiguous, show available names and ask once. If endpoint information
   would resolve ambiguity, inspect only the relevant candidates with the
   helper below. Do not select a fallback on failure.
4. Record the name, context root, relevant endpoint, and any required CF
   org/space. Keep that choice until the user changes it or its identity no
   longer matches. Expired credentials do not invalidate the choice.

Missing `cfctx-env`? Read [runtime.md](references/runtime.md#legacy-installations).
Do not install or upgrade tools as a side effect of selecting a foundation.

## 2. Inspect, then execute

Resolve `SKILL_DIR` to this skill's absolute directory. The bundled helper uses
Bash, `jq`, and the installed `cfctx-env`; it does not log in or enrich contexts.

```bash
bash "$SKILL_DIR/scripts/context.sh" inspect cdc
bash "$SKILL_DIR/scripts/context.sh" run cdc -- cf target
bash "$SKILL_DIR/scripts/context.sh" run cdc -- cf apps
```

Replace `cdc` with the confirmed name. `inspect` emits only the context root,
name, and configured endpoints/org/space. Compare the relevant endpoint with
the confirmed identity before the first operation and after recovery or a
context change. An unexpected endpoint change requires resolution, not silent
acceptance. Cache this inspection for an unchanged task/environment.

`run` clears inherited platform variables, checks loading succeeded, and checks
CF's cached API/org/space against configured values before executing CF commands.
For org/space-scoped operations, resolve any missing or conflicting org/space
before running. Never treat upstream defaults such as `system` as user intent.
For `om`, `bosh`, and `credhub`, compare the inspected endpoint to the intended
foundation and use the tool's read-only target/status check when needed; the
helper checks that its endpoint variable exists, not remote server identity.

Pass commands as arguments, keeping each value quoted; no `eval`, `sh -c`, or
interpolated command strings. For example:

```bash
bash "$SKILL_DIR/scripts/context.sh" run cdc -- cf app 'orders worker'
bash "$SKILL_DIR/scripts/context.sh" run cdc -- bosh vms
```

Do not pass endpoint/config overrides (for example `cf api`, `cf login`, `bosh -e`,
`om -t` or `--env`, or `credhub api`) that bypass the checked context. Review commands and scripts
for overrides; the helper is not a command authorization sandbox. Read
[runtime.md](references/runtime.md#org-and-space-changes) for intentional CF
org/space changes and [runtime.md](references/runtime.md#workspace-credentials)
when the workspace already supplies a `cfctx-run` descriptor/credential producer.

## 3. Recover only the failed prerequisite

| Observation | Action |
|---|---|
| Missing context, env file, endpoint, or target mismatch | Stop before the requested command. Resolve the exact context/configuration; never create a similarly named context automatically. |
| Explicit expired/invalid login | Keep the foundation. Follow the single-attempt recovery in [runtime.md](references/runtime.md#authentication). |
| SSO needs human interaction | Ask the user to authenticate the same context in their terminal, then verify again. Never request a password/passcode in chat. |
| DNS, timeout, connection, or TLS error | Report the observed category. At most one bounded diagnostic; no auth loop and no TLS bypass. |
| Forbidden / insufficient permissions | Report it; do not switch identities, foundations, or escalate roles. |
| Requested command fails | Preserve its exit status and explain the failure. Do not automatically replay a mutation whose outcome is uncertain. |

Loading environment variables, a zero switch exit code, or a printed
`cf logged in` message is **not proof of working authentication**. Use the
actual requested read-only operation as the authentication check where possible;
before a mutation, use a minimal authenticated read scoped to its target.

## Boundaries and completion

- Foundation selection supplies routing, not authorization for a deployment,
  deletion, credential change, enrichment, or persistent retargeting. Respect
  authority already present in the user's request; do not ask again for it.
- Keep secrets out of tool output. Never print raw `cfctx-env` exports, source
  files, CF config JSON, tokens, or unrestricted environment dumps. Do not use
  shell tracing. Context files are trusted local executable shell code, not
  untrusted files from a repository or attachment.
- `cfctx-env` reuses caches; it does not refresh tokens on ordinary loads.
  Reuse discovery and target decisions, but load the context for every command.
  Avoid `doctor --online`, enrichment, and login on the normal path.
- Report the foundation and relevant org/space, the command result, and any
  remaining blocker. Claim success only from the command's result, not setup
  output. Do not claim a tool call switched the user's other terminal shells.
