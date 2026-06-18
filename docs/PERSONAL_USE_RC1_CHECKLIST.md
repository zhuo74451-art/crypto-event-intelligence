# Personal-Use RC1 Checklist

## Code

- [ ] Alert state uses one durable truth source.
- [ ] Unchanged alerts are suppressed.
- [ ] Changed and resolved alerts are classified correctly.
- [ ] Delivery timestamp is written only after successful Telegram send.
- [ ] Publish-once sends at most one message.

## Server

- [ ] Feed loopback works.
- [ ] Whale data works.
- [ ] BTC / ETH / SOL / HYPE data works.
- [ ] One-shot exits cleanly.
- [ ] No orphan process remains.

## Telegram

- [ ] Chinese text is readable.
- [ ] Card has no repeated alert sections.
- [ ] Public card has no raw source-health debug list.
- [ ] Same unchanged signal does not send twice.
- [ ] Final message ID is recorded.

## Personal Operation

- [ ] Manual run command is documented.
- [ ] Optional 10-minute schedule example is documented.
- [ ] Exact stop command is documented.
- [ ] Status command is documented.
- [ ] Rollback command is documented.
