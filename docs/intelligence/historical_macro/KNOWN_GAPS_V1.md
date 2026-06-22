# Known Gaps V1

## Data Gaps

### Pre-Event Consensus Observations (P2)
- **Status**: Not yet gathered (P2 scope)
- **Reason**: Requires public archive scraping from ForexFactory, Investing.com, or similar sources
- **Impact**: All 1,658 events have `consensus_value: null`, surprise calculation not possible

### Revision History (P2)
- **Status**: Not yet built
- **Reason**: Requires ALFRED API access or BLS revision-specific endpoints
- **Impact**: 0 revision records captured

### Core PCE from BEA Direct
- **Status**: Worked around via FRED
- **Reason**: BEA NIPA API requires registration key for public access
- **Workaround**: Core PCE data sourced from FRED (PCEPILFE series)
- **Impact**: None — data still available via alternative source

### FOMC Rate Decisions from Fed Direct
- **Status**: Worked around via FRED
- **Reason**: Federal Reserve Board historical page URL structure changed
- **Workaround**: FOMC rate data sourced from FRED (FEDFUNDS series)
- **Impact**: None — data still available via alternative source

## Public Source Limitations

| Gap | Category | Details |
|-----|----------|---------|
| BEA direct API | Public source access requires registration | Registration available but key integration not done |
| Fed historical HTML | URL structure outdated | Needs updated URL patterns |
| ALFRED vintage data | API key required for vintage queries | Public API key available but not configured |
| ForexFactory consensus | HTML parsing fragile | Structure may change without notice |
| Strict pre-event archives | Limited public availability | Most archived pages are reconstructed, not strictly pre-event |

## Future Improvements (P3-P4)

- Add BEA registration key for direct Core PCE access
- Add FRED API key for ALFRED vintage revision queries
- Add optional families: Retail Sales, PPI, GDP, ISM, Jobless Claims, FOMC Minutes
- Implement multi-source consensus cross-validation
- Add DST boundary handling and release time zone verification
- Implement offline replay from cached snapshots
