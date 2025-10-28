#!/usr/bin/env bash
set -euo pipefail
site="$1"; resolver_in="${2:-127.0.0.1}"; mode="$3"; out="$4"; trials="${5:-5}"
mkdir -p "$(dirname "$out")"
isodate(){ date -u +"%Y-%m-%dT%H:%M:%SZ"; }

resolver_host="$resolver_in"
declare -a port_arg=()
if [[ "$resolver_in" == *"#"* ]]; then
  resolver_host="${resolver_in%%#*}"
  resolver_port="${resolver_in##*#}"
  port_arg=(-p "$resolver_port")
fi

flush(){
  if [[ "${COLD:-}" == "1" && -n "${FLUSH_CMD:-}" ]]; then
    if [[ "$FLUSH_CMD" == *"%s"* ]]; then
      printf -v _cmd "$FLUSH_CMD" "$site"
      eval "$_cmd" >/dev/null 2>&1 || true
    else
      eval "$FLUSH_CMD" >/dev/null 2>&1 || true
    fi
  fi
}

dns_time(){
  dig +tries=1 +time=5 +stats A "$site" @"$resolver_host" ${port_arg+"${port_arg[@]}"} 2>/dev/null \
    | awk '/Query time/ {print $4}'
}

for t in $(seq 1 "$trials"); do
  flush
  ms="$(dns_time)"; [[ -z "${ms:-}" ]] && ms="NA"
  echo "$(isodate),$mode,$site,$t,$ms,ok" >> "$out"
done
