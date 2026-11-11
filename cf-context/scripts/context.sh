#!/usr/bin/env bash
# Checked loading for existing, trusted cfctx contexts. No login or enrichment.
set -euo pipefail
set +x

fail() { printf 'cf-context: %s\n' "$*" >&2; exit 1; }
[[ $# -ge 2 ]] || fail 'usage: context.sh inspect NAME | run NAME -- COMMAND [ARG ...]'
mode=$1
name=$2
shift 2
case "$mode" in
  inspect) [[ $# -eq 0 ]] || fail 'inspect takes only a context name' ;;
  run)
    [[ $# -ge 2 && $1 == -- ]] || fail 'run requires -- COMMAND [ARG ...]'
    shift
    case "$1" in cf|om|bosh|credhub) ;; *) fail 'supported commands: cf, om, bosh, credhub' ;; esac
    ;;
  *) fail 'unknown mode' ;;
esac
case "$name" in
  ''|-*|.*|*/*|*[[:space:]]*) fail 'invalid context name' ;;
esac
command -v cfctx-env >/dev/null || fail 'cfctx-env is not installed or not on PATH'
command -v jq >/dev/null || fail 'jq is required for checked context loading'
root=${CFCTX_ROOT:-$HOME/.cf-homes}
[[ -d "$root/$name" ]] || fail 'context does not exist'
root=$(cd "$root" && pwd -P)
expected_home="$root/$name"
env_file="$expected_home/context.env"
[[ -f "$env_file" && -r "$env_file" ]] || fail 'context.env is missing or unreadable'
if perms=$(stat -c '%a' "$env_file" 2>/dev/null); then :
elif perms=$(stat -f '%Lp' "$env_file" 2>/dev/null); then :
else fail 'cannot check context.env permissions'; fi
[[ "$perms" == 600 || "$perms" == 400 ]] || fail 'context.env must have mode 600 or 400'

# cfctx-env does not unset absent variables. Clear before its source subprocess.
while IFS= read -r var; do
  case "$var" in CF_*|OM_*|BOSH_*|CREDHUB_*|UAA_*) unset "$var" ;; esac
done < <(compgen -v)
export CFCTX_ROOT="$root"
exports=$(cfctx-env "$name") || fail 'context loading failed; command was not run'
eval "$exports"
unset exports
[[ "${CF_HOME:-}" == "$expected_home" ]] || fail 'loaded CF_HOME does not match selected context'

if [[ "$mode" == inspect ]]; then
  jq -n --arg name "$name" --arg root "$root" \
    --arg cf "${CF_API:-}" --arg org "${CF_ORG:-}" --arg space "${CF_SPACE:-}" \
    --arg om "${OM_TARGET:-}" --arg bosh "${BOSH_ENVIRONMENT:-}" \
    --arg credhub "${CREDHUB_SERVER:-}" \
    '{name:$name,root:$root,cf:$cf,org:$org,space:$space,om:$om,bosh:$bosh,credhub:$credhub}'
  exit 0
fi

case "$1" in
  cf)
    [[ -n "${CF_API:-}" ]] || fail 'CF_API is missing'
    # Read only identity fields; never print the token-bearing config.
    jq -e --arg api "$CF_API" --arg org "${CF_ORG:-}" --arg space "${CF_SPACE:-}" \
      '.Target == $api and
       ($org == "" or .OrganizationFields.Name == $org) and
       ($space == "" or .SpaceFields.Name == $space)' \
      "$CF_HOME/.cf/config.json" >/dev/null 2>&1 \
      || fail 'cached CF API/org/space is missing or differs from context.env'
    ;;
  om) [[ -n "${OM_TARGET:-}" ]] || fail 'OM_TARGET is missing' ;;
  bosh) [[ -n "${BOSH_ENVIRONMENT:-}" ]] || fail 'BOSH_ENVIRONMENT is missing' ;;
  credhub) [[ -n "${CREDHUB_SERVER:-}" ]] || fail 'CREDHUB_SERVER is missing' ;;
esac
exec "$@"
