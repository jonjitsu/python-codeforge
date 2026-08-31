# Agent instructions

Use the repository skills in `.agents/skills` when their descriptions match the work.
For Python implementation, refactoring, testing, or review, follow the
`python-development` skill.

## Installable agent configuration

The root `.agents/skills` directory configures work on this repository only. It is independent
of the agent configuration distributed to consumers. Keep installable payload files under
`data/agent-config`; packaging and `ai.install-config` must read from that directory, never from
the repository-local `.agents` directory.
