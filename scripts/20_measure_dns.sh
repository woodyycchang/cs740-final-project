#!/usr/bin/env bash
set -euo pipefail
site="$1"; resolver_in="${2:-127.0.0.1}"; mode="$3"; out="$4"; trials="${5:-5}"
mkdir -p "$(dirname "$out")"

isodate(){ date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# parse host[#port]
resolver_host="$resolver_in"; port_arg=()
if [[ "$resolver_in" == *"#"* ]]; then
  resolver_host="${resolver_in%%#*}"
  resolver_port="${resolver_in##*#}"
  port_arg=(-p "$resolver_port")
fi

flush(){ [[ "${COLD:-}" == "1" && -n "${FLUSH_CMD:-}" ]] && eval "$FLUSH_CMD" || true; }

dns_time(){
  dig +tries=1 +time=5 +stats A "$site" @"$resolver_host" "${port_arg[@]}" 2>/dev/null \
    | awk '/Query time/ {print $4}'
}

for t in $(seq 1 "$trials"); do
  flush
  ms=$(dns_time || echo "NA")
  echo "$(isodate),$mode,$site,$t,$ms,ok" >> "$out"
done
