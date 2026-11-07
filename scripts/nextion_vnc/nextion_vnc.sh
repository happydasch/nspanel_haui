#!/usr/bin/env bash
# Open the Nextion Editor's Windows VM in a browser: websockify serves noVNC on
# 127.0.0.1 and bridges it to the VM's VNC server.
#
# Usage: scripts/nextion_vnc/nextion_vnc.sh   (Ctrl+C stops the bridge)
#
#   NEXTION_VNC_HOST  VNC server of the VM (default 192.168.65.2)
#   NEXTION_VNC_PORT  its VNC port (default 5900)
#   NOVNC_PORT        local web port (default 6080)
#
# The first run installs websockify into a venv and clones noVNC under
# build/novnc/ (git-ignored). The bridge listens on 127.0.0.1 only: the VNC
# password is all that guards the VM, so it is not exposed to the network.
set -euo pipefail

NOVNC_VERSION=v1.7.0
WEBSOCKIFY_VERSION=0.13.0

vnc_host="${NEXTION_VNC_HOST:-192.168.65.2}"
vnc_port="${NEXTION_VNC_PORT:-5900}"
web_port="${NOVNC_PORT:-6080}"

repo_root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
dir="$repo_root/build/novnc"
venv="$dir/websockify-$WEBSOCKIFY_VERSION"
novnc="$dir/noVNC-$NOVNC_VERSION"

if [[ ! -x "$venv/bin/websockify" ]]; then
  printf 'Installing websockify %s into %s\n' "$WEBSOCKIFY_VERSION" "$venv"
  python3 -m venv "$venv"
  "$venv/bin/pip" install --quiet --disable-pip-version-check "websockify==$WEBSOCKIFY_VERSION"
fi
if [[ ! -f "$novnc/vnc.html" ]]; then
  printf 'Cloning noVNC %s into %s\n' "$NOVNC_VERSION" "$novnc"
  git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$NOVNC_VERSION" \
    https://github.com/novnc/noVNC.git "$novnc"
fi

# websockify starts happily without the VM and fails each browser connection
# later; check up front so a stopped VM is reported here.
if ! "$venv/bin/python" -c 'import socket, sys; socket.create_connection((sys.argv[1], int(sys.argv[2])), 3).close()' \
  "$vnc_host" "$vnc_port" 2>/dev/null; then
  printf 'VNC server %s:%s is not reachable; start the Windows VM first.\n' \
    "$vnc_host" "$vnc_port" >&2
  exit 1
fi

printf 'Nextion Editor VM %s:%s\nOpen http://127.0.0.1:%s/vnc.html?autoconnect=true&resize=scale&reconnect=true\n' \
  "$vnc_host" "$vnc_port" "$web_port"
exec "$venv/bin/websockify" --web "$novnc" "127.0.0.1:$web_port" "$vnc_host:$vnc_port"
