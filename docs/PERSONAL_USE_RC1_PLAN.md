# Personal-Use RC1 Finalization Plan

Current integration baseline: `8a881601a6aaaaa130cb3ab788d4da8fd2ba6933`.

This repository is being finalized as a personal-use Telegram crypto signal tool. The goal is not enterprise infrastructure. The goal is one stable, understandable version that can run manually or on a simple schedule.

## RC1 Scope

The final RC1 must include only:

1. Live-public one-shot data collection.
2. Curated Feed loopback configuration.
3. Whale alert state and duplicate suppression.
4. Readable Telegram card rendering.
5. One explicit `publish-once` path.
6. One simple run command and one simple stop command.
7. One concise offline status command or script.

## RC1 Acceptance

- Same unchanged whale alert does not send repeatedly.
- New, materially changed, or resolved alerts can send.
- Telegram sends at most one message per publish invocation.
- Feed, Whale, BTC, ETH, SOL, and HYPE can be read in a server one-shot.
- Chinese card text is valid UTF-8.
- No raw source-health debug list in public cards.
- Errors are visible and do not expose the Bot Token.
- Manual run and stop steps are documented.
- No daemon, cron, or systemd service is enabled by default.

## Final GitHub Deliverable

Create one final PR from the latest `main`:

`release/personal-use-rc1`

The final PR should contain only missing RC1 work and a concise runbook. Avoid parallel implementations, enterprise deployment frameworks, dashboards, and broad refactors.

## Final Runbook Must Show

- install/update dependencies
- one-shot dry run
- publish-once dry run
- publish-once real staging send
- optional 10-minute schedule example
- exact stop/disable command
- status check
- rollback to the previous Git commit

## Non-Goals

- trading or private exchange APIs
- wallets or order execution
- paid APIs
- multi-user permissions
- complex release management
- enterprise observability
- microservices
