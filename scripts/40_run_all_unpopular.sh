#!/usr/bin/env bash
# Orchestrate the experiment across modes and unpopular sites.
# Output goes into data_for_submission/raw (aggregated by mode, like popular).
# Requires: yq (sudo apt install -y yq) and RESOLVER_IP env var set on client.

set -euo pipefail

OUT_DIR="data_for_submission/raw_unpop"
mkdir -p "$OUT_DIR"

if [[ -z "${RESOLVER_IP:-}" ]]; then
  echo "Set RESOLVER_IP to the resolver VM IP (e.g. 8.8.8.8 or 127.0.0.1)" >&2
  exit 1
fi

# Same style as main 40_run_all.sh, but using unpopular_sites.txt
modes=$(yq -r '.modes[]' config/modes.yml)
mapfile -t sites < <(shuf config/unpopular_sites.txt)

for mode in $modes; do
  ./scripts/10_dns_profiles.sh "$mode"

  dns_cold="$OUT_DIR/${mode}_dns_cold_unpopular.csv"
  dns_warm="$OUT_DIR/${mode}_dns_warm_unpopular.csv"
  web_cold="$OUT_DIR/${mode}_web_cold_unpopular.csv"
  web_warm="$OUT_DIR/${mode}_web_warm_unpopular.csv"

  # Start fresh for this mode
  rm -f "$dns_cold" "$dns_warm" "$web_cold" "$web_warm"

  for site in "${sites[@]}"; do
    safe_site=$(echo "$site" | sed 's|https\?://||; s|/|_|g')
    echo "UNPOPULAR mode=$mode site=$site resolver=$RESOLVER_IP"

    # ---- COLD ----
    if command -v unbound-control >/dev/null 2>&1; then
      sudo unbound-control flush_zone . || true
    else
      echo "Warning: unbound-control not found on this host, skipping resolver flush"
    fi
    sudo resolvectl flush-caches 2>/dev/null || true

    ./scripts/20_measure_dns.sh "$site" "$RESOLVER_IP" "$mode" "$dns_cold" 10

    tmpdir=$(mktemp -d)
    node scripts/30_measure_pageload.js "$site" "$mode" "$web_cold" "$tmpdir"
    rm -rf "$tmpdir"

    # ---- WARM ----
    node scripts/30_measure_pageload.js "$site" "$mode" /dev/null "$HOME/.warm-$mode-$safe_site" || true

    ./scripts/20_measure_dns.sh "$site" "$RESOLVER_IP" "$mode" "$dns_warm" 10
    node scripts/30_measure_pageload.js "$site" "$mode" "$web_warm" "$HOME/.warm-$mode-$safe_site" || true
  done
done

