#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Scanning tracked files for sensitive patterns..."

patterns=(
  'ghp_[A-Za-z0-9]{20,}'
  'github_pat_[A-Za-z0-9_]+'
  'sk-kimi-[A-Za-z0-9]+'
  'sk-[A-Za-z0-9]{20,}'
  'AIza[0-9A-Za-z\-_]{20,}'
  'BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY'
  'docs\.google\.com/spreadsheets/d/'
  'r\.jina\.ai'
)

ignore_globs=(
  ':!backend/.env'
  ':!.env'
  ':!.env.local'
  ':!.env.*.local'
)

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT

git ls-files -z -- . "${ignore_globs[@]}" \
  | xargs -0 -r rg -n -I -H -e "${patterns[0]}" \
  >"$tmpfile" || true

for ((i=1; i<${#patterns[@]}; i++)); do
  git ls-files -z -- . "${ignore_globs[@]}" \
    | xargs -0 -r rg -n -I -H -e "${patterns[$i]}" \
    >>"$tmpfile" || true
done

sort -u "$tmpfile" -o "$tmpfile"

if [[ -s "$tmpfile" ]]; then
  echo
  echo "Sensitive-looking content found:"
  cat "$tmpfile"
  echo
  echo "Push check failed."
  exit 1
fi

echo "No sensitive patterns found in tracked files."
