---
name: status
description: Show the chef status of this project and session - active level, .chef.md overrides, recorded decisions, detected stacks and the session token usage. Use when the user runs /chef:status or asks what chef level is on or how many tokens this session used.
---

# Status

Run this command and print its output as is, in a code block. Say nothing else.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/status/scripts/usage.sh"
```

The script finds the current session transcript itself. If it exits with an error, print its error line and stop.
