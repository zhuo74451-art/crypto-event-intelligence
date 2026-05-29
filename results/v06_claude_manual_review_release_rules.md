# Conservative Auto-Release Rules (v0.6)

## AUTO-RELEASE CRITERIA (manual_review_required=FALSE)
**ALL conditions must be met:**

1. `label_origin` = `auto_provisional` AND `confidence >= 0.95`
2. `manual_decision` = `discard`
3. `route` â {`research_only`, `unsupported_research`}
4. `scope` â {`research_only`, `unknown`}
5. No trading signals, price targets, or directional calls in content
6. No macro_policy route entries

**Expected release:** ~35 rows (high-conf discards)

---

## MANDATORY HOLDOUT (manual_review_required=TRUE)

| Criterion | Reason |
|-----------|--------|
| `label_origin` = `auto_medium_conf_review_required` | All 9 rows |
| `manual_decision` = `approve_publish` | All 17 rows (publish gate) |
| `manual_decision` = `keep_review` | All 7 rows (unresolved) |
| `route` = `macro_policy` | All 40 rows (policy risk) |
| `route` = `alpha_candidate` | All 4 rows (trading-adjacent) |
| `scope` = `market_wide` | All 32 rows (systemic impact) |
| `scope` = `multi_asset` | All 15 rows (correlation risk) |
| `confidence < 0.95` | All rows |

**Holdout floor:** ~59 rows â target â¤20 rows after review

---

## IMPLEMENTATION
- Auto-release only `discard` + `research_only/unsupported` + `confâ¥0.95`
- Route all others to manual queue
- Disable auto_publish; require explicit approval for `approve_publish` class
