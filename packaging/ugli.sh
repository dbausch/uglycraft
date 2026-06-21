#!/bin/bash
UGLI=/usr/share/ugli/UGLI_2
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/ugli"
mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

fs=false
args=()
for arg in "$@"; do
  case "$arg" in
    -h|--help) exec "$UGLI" "$@" ;;
    -f|--fs) fs=true ;;
    *) args+=("$arg") ;;
  esac
done

if [ "$fs" = true ]; then
  if [ -n "$TERMINAL_FS" ]; then
    exec $TERMINAL_FS "$UGLI" "${args[@]}"
  elif command -v kitty >/dev/null 2>&1; then
    exec kitty \
      -c /usr/share/ugli/ANSI-87.conf \
      -o font_family="Liberation Mono" \
      -o font_size=28 \
      -o remember_window_size=false \
      -o initial_window_height=25c \
      -o initial_window_width=80c \
      -o 'single_window_padding_width=1 58.5' \
      --start-as=fullscreen \
      -- "$UGLI" "${args[@]}"
  else
    exec "$UGLI" "${args[@]}"
  fi
elif [ -n "$TERMINAL" ]; then
  exec $TERMINAL "$UGLI" "${args[@]}"
elif command -v kitty >/dev/null 2>&1; then
  exec kitty \
    -c /usr/share/ugli/ANSI-87.conf \
    -o font_family="Liberation Mono" \
    -o font_size=16 \
    -o remember_window_size=false \
    -o initial_window_height=25c \
    -o initial_window_width=80c \
    -- "$UGLI" "${args[@]}"
else
  exec "$UGLI" "${args[@]}"
fi
