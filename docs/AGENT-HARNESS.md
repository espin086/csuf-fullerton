# Shared Claude and Codex harness

`AGENTS.md` is the single shared entry point. Claude imports it from `CLAUDE.md`.
Codex discovers individual symlinked folders under `.agents/skills/`, each resolving to
an existing `.claude/skills/<name>`. `.agents/rules` links to `.claude/rules`; AGENTS tells
Codex to open applicable rules explicitly. No skill or rule body is duplicated.

Run `bash scripts/check-agent-links.sh` after checkout. Use a real Git clone with symlink
support; on Windows use WSL or enable Developer Mode and Git symlinks before checkout.
A downloaded archive with links converted into text files is not a working harness.

Restart each agent after the change. In Claude, `/context` should show CLAUDE/AGENTS; invoke
`/propose`. In Codex, ask for the active instruction sources and invoke `$propose`; it should
read the linked skill and first identify the issue. Confirm neither proceeds to app code
while the planning PR is unmerged. Do not grant extra filesystem access just to run this check.

The local/CI link check proves the filesystem contract. It does not prove model compliance.
Claude's hook JSON, slash-command routing, subagents and tool permission allowlists remain
Claude-specific. Codex has its own `.codex/config.toml`; do not copy Claude's settings there.
GitHub rules/checks are the common merge controls, with the current limitations described
in CONTRIBUTING. Agent secrets remain in the user's credential store, outside the checkout.

Sources: [Codex skills](https://developers.openai.com/codex/skills),
[Codex instructions](https://developers.openai.com/codex/guides/agents-md),
[Claude AGENTS imports](https://code.claude.com/docs/en/memory#agentsmd).
