#!/usr/bin/env bash
# Orchestrate the experiment across modes and sites.
# Requires: yq (sudo apt install -y yq) and RESOLVER_IP env var set on client.
set -euo pipefail
if [[ -z "${RESOLVER_IP:-}" ]]; then
  echo "Set RESOLVER_IP to the resolver VM IP" >&2; exit 1
fi

modes=$(yq -r '.modes[]' config/modes.yml)
# mapfile -t sites < <(shuf config/sites.txt)
mapfile -t sites < <(shuf config/unpopular_sites.txt)

for mode in $modes; do
  ./scripts/10_dns_profiles.sh "$mode"
  for site in "${sites[@]}"; do
    echo "DEBUG: mode=$mode, site=$site, resolver=$RESOLVER_IP"
    # COLD
    ssh "Ryan7777@$RESOLVER_IP" 'sudo unbound-control flush_zone . || sudo systemctl restart unbound' || true
    sudo resolvectl flush-caches || true
    ./scripts/20_measure_dns.sh "$site" "$RESOLVER_IP" "$mode" new_data/unpop_raw/doh_dns_cold.csv 5
    tmpdir=$(mktemp -d)
    node scripts/30_measure_pageload.js "$site" "$mode" new_data/unpop_raw/doh_web_cold.csv "$tmpdir"
    rm -rf "$tmpdir"
    # WARM
    node scripts/30_measure_pageload.js "$site" "$mode" /dev/null "$HOME/.warm-$mode-$site" || true
    ./scripts/20_measure_dns.sh "$site" "$RESOLVER_IP" "$mode" new_data/unpop_raw/doh_dns_warm.csv 5
    node scripts/30_measure_pageload.js "$site" "$mode" new_data/unpop_raw/doh_web_warm.csv "$HOME/.warm-$mode-$site" || true
  done
done
