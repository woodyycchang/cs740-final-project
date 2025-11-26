#!/usr/bin/env bash
# Orchestrate the experiment across modes and sites.
# Requires: yq (sudo apt install -y yq) and RESOLVER_IP env var set on client.
set -euo pipefail
mkdir -p data/raw/dns data/raw/web

if [[ -z "${RESOLVER_IP:-}" ]]; then
  echo "Set RESOLVER_IP to the resolver VM IP" >&2; exit 1
fi

modes=$(/snap/bin/yq '.modes[]' config/modes.yml)
mapfile -t sites < <(shuf config/unpopular_sites.txt)

for mode in $modes; do
  ./scripts/10_dns_profiles.sh "$mode"
  for site in "${sites[@]}"; do
    safe_site=$(echo "$site" | sed 's|https\?://||; s|/|_|g')
    # COLD
    if command -v unbound-control >/dev/null 2>&1; then
        sudo unbound-control flush_zone . || true
    else
        echo "Warning: unbound-control not found, skipping flush"
    fi
    sudo resolvectl flush-caches || true
    dns_out="data/raw/dns/${safe_site}_${mode}_cold.csv"
    web_out="data/raw/web/${safe_site}_${mode}_cold.csv"
    ./scripts/20_measure_dns.sh "$site" "$RESOLVER_IP" "$mode" "$dns_out" 5
    tmpdir=$(mktemp -d)
    node scripts/30_measure_pageload.js "$site" "$mode" "$web_out" "$tmpdir"
    rm -rf "$tmpdir"
    # WARM
    node scripts/30_measure_pageload.js "$site" "$mode" /dev/null "$HOME/.warm-$mode-$safe_site" || true
    
    dns_out="data/raw/dns/${safe_site}_${mode}_warm.csv"
    web_out="data/raw/web/${safe_site}_${mode}_warm.csv"
    ./scripts/20_measure_dns.sh "$site" "$RESOLVER_IP" "$mode" "$dns_out" 5
    node scripts/30_measure_pageload.js "$site" "$mode" "$web_out" "$HOME/.warm-$mode-$safe_site"
  done
done
