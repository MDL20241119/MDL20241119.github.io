#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
python3 start_web.py "$@"
result=$?
if [ "$result" -ne 0 ]; then
  printf '\nPython 3.12 or later is required. Press Enter to close.\n'
  read -r reply
fi
exit "$result"
