# command notes

## preferred official resume flows

- `claude --continue`: continue the most recent conversation in the current directory
- `claude --resume`: open the session picker
- `claude --resume <name-or-id>`: resume a known session by name or id
- `/resume`: switch conversations from inside an active session
- `/rename <session-name>`: make the session easier to find later

## context-management commands

- `/compact [instructions]`: summarize the session and keep the thread alive
- `/clear`: reset conversation history for unrelated work after preserving the current task

## usage and status wording

Users may say `/usage`, but currently documented wording is different.

- `/cost`: token usage statistics, especially relevant for api users
- `/stats`: subscriber usage patterns
- `/status`: account and system status

If the local install behaves differently, verify with `/help` and `claude --version`.

## third-party helper

`claude-auto-resume` is a third-party GitHub project, not an official Anthropic feature. Mention it only as an optional convenience for long waits after usage limits. Prefer built-in resume commands first.
