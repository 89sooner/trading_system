# CLAUDE.md

@AGENTS.md

## Claude Code specific rules

- Use `AGENTS.md` as the shared repository policy, then apply the Claude-specific command policy below.
- Prefer `rg` over `grep` for text search.
- Prefer `fd` or `fdfind` over `find` for file discovery.
- Prefer `jq` for JSON inspection.
- Prefer `git grep` when searching tracked files only.
- Prefer `sed`, `head`, and `tail` over broad `cat`.
- Prefer non-interactive commands when possible.
- Prefer machine-readable output such as JSON when available.
- Keep shell output narrow. Read the smallest relevant scope first, then expand only if needed.
- Search the smallest relevant package or directory first before scanning the whole repository.
- If `rg`, `fd` or `fdfind`, or `jq` are missing, install them before broad repository analysis.
- If modern tools are unavailable, install them first when practical. Otherwise use the narrowest compatible fallback.

## Install-first policy

If required tools are missing, install them first.

Debian or Ubuntu:

- `apt-get update && apt-get install -y ripgrep fd-find jq`

If `fd` is installed as `fdfind`:

- `alias fd=fdfind`

macOS with Homebrew:

- `brew install ripgrep fd jq`

## Search policy

- Do not use `grep`, `egrep`, `fgrep`, or `find` for normal repository exploration when `rg`, `fd` or `fdfind`, `jq`, `git grep`, `sed`, `head`, or `tail` can answer the same question.
- Use `git grep` instead of plain `grep` when the search target is tracked files.
- Search the smallest relevant package or directory first.
- Avoid broad recursive scans unless they are necessary.
- Prefer filename-only searches when possible.
- Prefer count or scoped searches before opening many files.
- Prefer machine-readable command output when a tool supports it.

## Practical defaults

- For text search, start with `rg`.
- For file discovery, start with `fd` or `fdfind`.
- For tracked code search, use `git grep`.
- For JSON output, parse with `jq`.
- For file reads, use `sed -n`, `head`, or `tail` before broader reads.
- For API or CLI inspection, prefer JSON output and narrow filtering over verbose raw output.
