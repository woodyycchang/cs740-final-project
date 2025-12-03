#!/usr/bin/env bash
# Run the experiment for all modes and sites.
# - public_udp:   RESOLVER_IP=8.8.8.8   (or other public resolver)
# - doh / dot:    RESOLVER_IP=127.0.0.1 (local DoH/DoT stub on node0)
# - local_cache:  RESOLVER_IP=10.10.1.2 (unbound on node1)

set -euo pipefail

OUT_DIR="data_ryan/raw"
mkdir -p "$OUT_DIR"

if [[ -z "${RESOLVER_IP:-}" ]]; then
  echo "Set RESOLVER_IP to the DNS server IP (e.g. 8.8.8.8, 127.0.0.1, or 10.10.1.2)" >&2
  exit 1
fi

# Modes come from config/modes.yml (e.g. public_udp, doh, dot, local_cache)
modes=$(yq -r '.modes[]' config/modes.yml)

# Sites list
mapfile -t sites < config/unpopular_sites.txt

for mode in $modes; do
  ./scripts/10_dns_profiles.sh "$mode"

  dns_cold="$OUT_DIR/${mode}_dns_cold.csv"
  dns_warm="$OUT_DIR/${mode}_dns_warm.csv"
  web_cold="$OUT_DIR/${mode}_web_cold.csv"
  web_warm="$OUT_DIR/${mode}_web_warm.csv"

  rm -f "$dns_cold" "$dns_warm" "$web_cold" "$web_warm"

  for site in "${sites[@]}"; do
    echo "mode=$mode site=$site resolver=$RESOLVER_IP"

    # ---- COLD ----
    # Clear any local DNS cache on node0 (if it exists)
    sudo resolvectl flush-caches 2>/dev/null || true

    # DNS cold: 10 queries
    ./scripts/20_measure_dns.sh "$site" "$RESOLVER_IP" "$mode" "$dns_cold" 10

    # Web cold: one pageload
    tmpdir=$(mktemp -d)
    node scripts/30_measure_pageload.js "$site" "$mode" "$web_cold" "$tmpdir"
    rm -rf "$tmpdir"

    # ---- WARM ----
    # Warm browser / connections a bit
    node scripts/30_measure_pageload.js "$site" "$mode" /dev/null "$HOME/.warm-$mode-$site" || true

    # DNS warm: 10 queries (resolver is now warm for this site)
    ./scripts/20_measure_dns.sh "$site" "$RESOLVER_IP" "$mode" "$dns_warm" 10

    # Web warm
    node scripts/30_measure_pageload.js "$site" "$mode" "$web_warm" "$HOME/.warm-$mode-$site" || true
  done
done

