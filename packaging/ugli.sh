#!/bin/bash
UGLI=/usr/share/ugli/UGLI_2
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/ugli"
mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

for arg in "$@"; do
  case "$arg" in -h|--help)
    exec "$UGLI" "$@" ;; esac
done

if [ -n "$TERMINAL" ]; then
  exec $TERMINAL "$UGLI" "$@"
elif command -v kitty >/dev/null 2>&1; then
  exec kitty \
    -c /usr/share/ugli/ANSI-87.conf \
    -o font_family="Liberation Mono" \
    -o font_size=16 \
    -o remember_window_size=false \
    -o initial_window_height=25c \
    -o initial_window_width=80c \
    -- "$UGLI" "$@"
else
  exec "$UGLI" "$@"
fi
