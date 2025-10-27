#!/usr/bin/env bash
# Usage: ./scripts/10_dns_profiles.sh <mode>
# This script prints guidance for switching the resolver to a given mode.
# In practice, you will edit your resolver VM (unbound/stubby/cloudflared) to match.
set -euo pipefail
mode=${1:-}
if [[ -z "$mode" ]]; then
  echo "Specify a mode: public_udp | dot | doh | local_cache" >&2
  exit 1
fi

case "$mode" in
  public_udp)
    echo "Switch resolver to forward "." to 8.8.8.8@53, 1.1.1.1@53 via unbound";;
  dot)
    echo "Run stubby on 127.0.0.1:8053 → upstreams: tls://1.1.1.1, tls://dns.google and have unbound forward to 127.0.0.1#8053";;
  doh)
    echo "Run cloudflared proxy-dns on 127.0.0.1:8054 and have unbound forward to 127.0.0.1#8054";;
  local_cache)
    echo "Run unbound as a full recursive resolver (no forward-zone), QNAME minimization on";;
  *)
    echo "Unknown mode: $mode" >&2; exit 2;;
esac

echo "(This script is a scaffold; implement your resolver switching on the resolver VM.)"
