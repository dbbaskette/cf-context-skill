#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
source_dir='/Volumes/My Shared Files/source'
results_dir='/Volumes/My Shared Files/results'
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT
cp -R "$source_dir/." "$work_dir/"
cd "$work_dir"
exec > >(tee "$results_dir/tests.log") 2>&1
sw_vers
bash --version
python3 --version
jq --version
bash -n install.sh cf-context/scripts/context.sh scripts/ci/guest-test.sh
python3 -m unittest discover -s tests -v
printf 'PASS\n' > "$results_dir/result.txt"
