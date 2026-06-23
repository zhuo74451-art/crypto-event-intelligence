# Known Gaps V1

## Dependency Gaps
- Lane A (Historical Macro Evidence): Not yet consumed — branch may exist but artifacts not integrated
- Lane B (Historical Market Cross-Asset): Not yet consumed — branch may exist but artifacts not integrated
- Without Lane A/B artifacts, replay uses hardcoded sample events only

## Coverage Gaps
- Real event count limited to temporary samples (~10 hardcoded events)
- No Lane A consensus/revision chain integration
- No Lane B market window/cross-asset/derivative integration
- Weekend event handling not tested
- Traditional market closure handling not tested

## Feature Gaps
- Vertical expansion (regulation, catalyst, forced flow) not implemented
- SQLite index not yet built
- Multi-horizon support present in contracts but limited in replay engine
- No incremental replay checkpointing implemented
- No parallel shard replay

## Maturity Labels
- Macro strategies: alpha (contracts valid, real replay pending)
- Regulation/Catalyst/Forced flow: not started
- Baselines: complete (8 families)
- Audits: scripted but not run against real data
