---
name: status
description: Show the chef status of this project and session - active level, .chef.md overrides, recorded decisions, detected stacks and the session token usage. Use when the user runs /chef:status or asks what chef level is on or how many tokens this session used.
---

# Status

Run this command and print its output as is, in a code block. Say nothing else.

```bash
CHEF_SESSION_ID="${CLAUDE_SESSION_ID}" bash "${CLAUDE_PLUGIN_ROOT}/skills/status/scripts/usage.sh"
```

The script reads this session's transcript (by session id). If it exits with an error, print its error line and stop.
