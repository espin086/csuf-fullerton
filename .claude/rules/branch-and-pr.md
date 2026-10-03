# Small commits and pull requests

Follow `CONTRIBUTING.md` for both humans and agents: issue, planning PR, maintainer merges
plan, then implementation PR. Never implement a capability against an unmerged plan.
Use a fresh branch from the merged plan on the default branch; never commit to main.

One coherent commit per completed task, with its tests and changelog. Aim for 1–3 related
tasks and about 300 hand-written lines per PR; explain necessary atomic exceptions.
Split independent capabilities. Preserve reviewed history; fix findings in new commits.
Use Conventional Commits and fill every applicable `.github/pull_request_template.md` field.
Agents push branches/open PRs and address review findings. The maintainer merges.
