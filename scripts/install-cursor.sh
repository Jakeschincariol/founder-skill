#!/usr/bin/env bash
# Copies skills/founder-* into the user Cursor skills folder.
# Does not write into ~/.cursor/skills-cursor or into the open project.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
dest="${HOME}/.cursor/skills"
case "$dest" in
  *skills-cursor*)
    echo "Refusing to install into skills-cursor." >&2
    exit 1
    ;;
esac
mkdir -p "$dest"
found=0
for dir in "$root"/skills/founder-*; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  rm -rf "$dest/$name"
  cp -R "$dir" "$dest/$name"
  echo "installed $name"
  found=1
done
if [ "$found" -ne 1 ]; then
  echo "No founder-* skill folders under $root/skills" >&2
  exit 1
fi
echo "Reload Cursor, then type /founder-board"
