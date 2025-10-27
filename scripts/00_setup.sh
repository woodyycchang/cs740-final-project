#!/usr/bin/env bash
set -euo pipefail
sudo apt update
sudo apt install -y jq curl bind9-dnsutils knot-dnsutils unbound stubby cloudflared \
  chromium-browser nodejs npm ntpdate tcpdump yq
sudo ntpdate pool.ntp.org || true
echo "Done. Install versions:"
chromium-browser --version || true
node --version || true
dig -v || true
kdig -v || true
