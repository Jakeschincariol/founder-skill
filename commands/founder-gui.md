---
description: Open Founder GUI, a live web view of this project's founder/ folder (every step, suggestion and result of the founder skills)
argument-hint: "[path to the project, default: this folder]"
allowed-tools: Bash(python3:*)
---

Founder GUI was started (or the running hub was told about this folder):

!`python3 "${CLAUDE_PLUGIN_ROOT}/gui/serve.py" --detach --dir "$ARGUMENTS"`

Tell the user, in one or two lines, the URL printed above and that the page
updates by itself while any founder skill writes to `founder/`. Mention that one
hub serves every project, so running this command in another folder adds that
project to the same page. If the output shows an error, show it and suggest
`python3 gui/serve.py --dir <project>` from the plugin folder to see more.
