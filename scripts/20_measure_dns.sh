#!/usr/bin/env bash
# Usage: ./scripts/20_measure_dns.sh <site> <resolver_ip> <mode> <out_csv> [trials=5]
set -euo pipefail
site="$1"; resolver_ip="${2:-127.0.0.1}"; mode="$3"; out="$4"; trials="${5:-5}"
mkdir -p "$(dirname "$out")"

isodate() {
  if date -Is >/dev/null 2>&1; then
    date -Is
  else
    date -u +"%Y-%m-%dT%H:%M:%SZ"
  fi
}

dns_time() {
  # We always query our resolver_ip; underlying transport is handled by the resolver profile.
  dig +tries=1 +time=5 +stats A "$site" @"$resolver_ip" 2>/dev/null | awk '/Query time/ {print $4}'
}

for t in $(seq 1 "$trials"); do
  if command -v resolvectl >/dev/null 2>&1; then sudo resolvectl flush-caches 2>/dev/null || true; fi
  ms=$(dns_time || echo "NA")
  echo "$(isodate),$mode,$site,$t,$ms,ok" >> "$out"
done
