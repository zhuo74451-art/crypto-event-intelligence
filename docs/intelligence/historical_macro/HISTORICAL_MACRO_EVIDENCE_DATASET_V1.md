# Historical Macro Evidence Dataset V1

## Dataset Identity

| Property | Value |
|----------|-------|
| Dataset Name | macro_evidence_v1 |
| Contract Version | 1.0.0 |
| Producer Lane | lane_a_historical_macro_evidence |
| Repository | zhuo74451-art/crypto-event-intelligence |
| Base SHA | 5a5ca58253479403f65ec726016d1ca9b91703d1 |

## Coverage

- **Period**: 2010-01 to 2026-12
- **Event Families**: 6 (us_cpi, us_core_cpi, us_nonfarm_payrolls, us_unemployment_rate, us_core_pce, us_fomc_rate_decision)
- **Release Events**: 1,658
- **Source Snapshots**: 226
- **Revision Records**: 0 (P2 scope)
- **Consensus Observations**: 0 (P2 scope)

## Data Sources

| Provider | Families | Series |
|----------|----------|--------|
| BLS (Bureau of Labor Statistics) | CPI, Core CPI, NFP, Unemployment | CUUR0000SA0, CUUR0000SA0L1E, CES0000000001, LNS14000000 |
| FRED (St. Louis Fed) | CPI, Core CPI, NFP, Unemployment, Core PCE, FOMC Rate | CPIAUCSL, CPILFESL, PAYEMS, UNRATE, PCEPILFE, FEDFUNDS |

## Point-in-Time Quality

All records currently have `point_in_time_quality: "missing"` for consensus, as pre-event consensus gathering is P2 scope.

## File Layout

```
data/intelligence/historical_macro/
  normalized/
    macro_release_events_v1.jsonl      # Canonical release events
    macro_source_snapshots_v1.jsonl    # Fetch metadata records
    macro_release_events_v1.csv        # Tabular summary
    quarantine/                        # Leakage isolation (empty)
  indexes/
    macro_evidence_v1.sqlite           # SQLite index with foreign keys
  reports/
    pit_audit_v1.json                  # Point-in-time audit results
    pit_audit_v1.md
    coverage_report_v1.json            # Coverage statistics
    coverage_report_v1.md
```

## Consumer Notes

- Use `actual_initial` for historical replay at release time
- Use `prior_as_known_then` for what was known before release
- Apply revision chain via `MacroAsOfEngine.get_release_as_of()` for any as-of date
- `consensus_value` is null until P2 consensus pipeline runs
- Missing consensus requires abstention in strategy layer
