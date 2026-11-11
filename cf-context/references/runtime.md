# Runtime and recovery

Load only the section needed for the current failure or execution mode.

## Authentication

An ordinary `cfctx-env NAME` load does not authenticate. `cf target` and cached
config checks describe local state; neither proves the server accepts a token.

For a clearly rejected/expired CF login:

1. Retain the selected foundation. Check `cfctx-env --help` for `--login`
   support without displaying any exports or credentials.
2. If this context already has an authorized automation client configured,
   attempt `cfctx-env --login NAME` **once**, in a clean platform environment.
   Use the cleanup loop in `scripts/context.sh` before invoking it (do not use
   `run ... -- cfctx-env`; that helper intentionally accepts only platform CLIs).
   The upstream login path sources the env file, so check its permissions as
   the helper does. No new client, role, auth-mode change, or credential lookup
   is implied. Do not use it for password or human SSO contexts.
3. Otherwise use the existing shell integration for one same-context recovery
   only if its configured auth method is suitable for automation. Set
   `CFCTX_FORCE_ACTOR=automation`, suppress enrichment with `--no-enrich`, and
   inspect failure messages: upstream can return zero after authentication fails.
4. If human SSO is required, have the user run `cfctx sso NAME` in their own
   configured terminal. Do not collect the passcode or loop on a headless prompt.
5. Inspect and verify again. Retry a read-only operation once. For a mutation,
   first determine whether any effect occurred; never replay it just because
   authentication was repaired. Stop if the recovery or verification fails.

A permission denial is not an expired token. A transport or TLS failure is not
proof of an authentication failure or a down foundation. If a network probe
would help, use the confirmed HTTPS API with certificate validation and a short
timeout, for example `curl --connect-timeout 3 --max-time 8 --output /dev/null
--write-out '%{http_code}\n' URL`. Inspect the curl exit status and error, not
just `000` (which also covers certificate errors). Do not add `-k`.

## Org and space changes

`cfctx-env` loads `CF_ORG` / `CF_SPACE` but does not apply them to CF's cached
CLI target. The bundled helper refuses a mismatch rather than guessing.

When the user authorizes an org/space change, load the same confirmed context
with the checked assignment below and use `cf target -o ORG -s SPACE`. Verify
API identity before retargeting and check the result afterward. This changes
shared cached state for that context; it is not isolated to the current shell.
Do not run simultaneous retargeting or authentication against the same context.

If the user requests a permanent default, `cfctx target NAME --org ORG --space
SPACE` persists both into `context.env`. Do not add these flags merely to inspect
a target. An intentional temporary target may differ from the saved defaults;
use a reviewed one-off invocation with explicit expected API/org/space instead
of weakening the helper's checks or editing defaults to make it pass.

## Legacy installations

Prefer `cfctx-env` when present. If absent, check the shell actually configured
by the user: `zsh -ic 'command -v cfctx'` or `bash -ic 'command -v cfctx'`.
Do not assume zsh on every platform. Source a known installation only when its
path is established; do not scan credential directories or rewrite rc files.

`cfctx ls` is a display format: a current-context line begins with `*`, followed
by the name, an optional `[env]`, and an optional URL. Ignore shell banners and
strip the marker; the first token is not always a foundation name. Names from
`cfctx-env --list` avoid this parsing altogether.

After selecting an existing context, verify that its directory and readable,
private `context.env` exist **before** invoking `cfctx target NAME`. A typo in
noninteractive upstream `cfctx` can create a new blank context. Do not use
`--create`, `--force`, `init-env`, or `enrich` to repair a selection failure.

For the fallback, use a reviewed temporary script with restrictive permissions
and pass the context name as a positional argument. Within the configured shell:
clear inherited platform variables, disable interactive auth with
`CFCTX_FORCE_ACTOR=automation`, switch using `cfctx target "$name" --no-enrich
--no-login`, then verify the loaded endpoint, CF_HOME, and actual CLI target
before executing. Keep load, verification, and command in the same invocation.
A successful switch alone is insufficient: source/auth failures may be swallowed.
If any of these checks cannot be established, stop and report the missing
prerequisite rather than running against the previous target.

Do not replace this with `eval "$(cfctx-env NAME)" && command`: `eval` can return
success even when the substitution failed. When a reviewed one-off invocation is
needed, first clear inherited `CF_*`, `OM_*`, `BOSH_*`, `CREDHUB_*`, and `UAA_*`
variables as in the helper, then check the assignment separately:

```bash
exports=$(cfctx-env "$name") || exit 1
eval "$exports" || exit 1
unset exports
# Verify CF_HOME and the relevant endpoint/CLI target before executing.
```

Never print `exports`. It contains secrets. This evaluates output from a trusted
installed helper and trusted local context files; it is not a general parser for
untrusted shell text. `cfctx env` masks selected variable names, but that is not
proof every possible secret was redacted; prefer the bundled narrow `inspect`.

## Workspace credentials

Upstream also has a separate `cfctx-run` binary. Use it when this workspace is
already provisioned with a trusted descriptor or credential producer; do not
invent a provider, capability, secret path, or descriptor from a foundation name.
This route can replace local context discovery: validate the explicitly intended
foundation and endpoints against the provisioned descriptor instead.

For an existing descriptor, use its exact selectors:

```bash
cfctx-run --provider mcp --workspace WORKSPACE --foundation FOUNDATION \
  --capability CAPABILITY --descriptor /absolute/path/descriptor.json -- cf apps
```

The runner verifies configured CF/BOSH identities in isolated state on every
invocation. It is installed separately and does not supply general isolation for
`om`, `credhub`, or `uaac`. For an already supplied request producer, check
`cfctx-run --contract` before using its request-fd contract. Credentials belong
in the producer's anonymous pipe, never argv, model-visible output, or a file.
Consult the pinned upstream contract below for this mode; do not improvise it.

## Reviewed upstream behavior

Reviewed against commit `dce4f37d0c8c31542b45d8cc7bc96eafe7b68f7c`:

- [Standalone helper](https://github.com/nkuhn-vmw/cfctx/blob/dce4f37d0c8c31542b45d8cc7bc96eafe7b68f7c/bin/cfctx-env): `--list`, cached exports, optional client `--login`; absent variables are not cleared, and env files are sourced as shell code.
- [Shell implementation](https://github.com/nkuhn-vmw/cfctx/blob/dce4f37d0c8c31542b45d8cc7bc96eafe7b68f7c/cfctx.sh): `_cfctx_cmd_ls` marker, `_cfctx_cmd_target` creation/persistence, `_cfctx_auto_login` soft failures, `_cfctx_cmd_switch` source failures.
- [Workspace contract](https://github.com/nkuhn-vmw/cfctx/blob/dce4f37d0c8c31542b45d8cc7bc96eafe7b68f7c/docs/workspace-credentials.md): isolated execution and its limits.

Check installed capabilities rather than assuming the README's version heading
implies every helper or flag is installed. No live foundation is needed to test
the bundled helper; the repository tests use disposable contexts and fake CLIs.
