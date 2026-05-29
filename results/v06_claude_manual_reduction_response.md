# Crypto Event Intelligence: Labeling Automation Decision

## 1. Decision Table: AI vs Human by Step

| Step | Owner | Confidence Threshold | Audit Sample | Rollback Trigger |
|------|-------|----------------------|---------------|------------------|
| **Candidate Classification** (event/noise) | AI | 85% | 5% weekly | <80% precision on holdout |
| **Asset Attribution** (which token/chain) | AI | 90% | 3% weekly | >2 false positives/100 events |
| **Event Taxonomy** (governance/exploit/listing/etc) | AI | 80% | 10% weekly | taxonomy drift >5% disagreement |
| **Timezone Normalization** | AI | 99% | 1% spot-check | any UTC conversion error |
| **Low-Risk Discard** (spam/duplicate/stale) | AI | 92% | 2% weekly | >1 false negative/week |
| **Publish-Review Approval** | AI + Human gate | 75% AI score | 100% of <75% | manual queue >20 items |

**Rationale:** Manual review only on borderline cases (<75% AI confidence). Discard the 59 manual_review_required backlogâretrain on them as negative examples, don't label them.

---

## 2. This Week Plan

- **MonâTue:** Audit the 59 manual_review_required items â categorize as:
  - Mislabeled (retrain signal)
  - Genuinely ambiguous (set as holdout test set, don't label)
  - Low-signal noise (discard)
  
- **WedâThu:** Build confidence-scoring layer:
  - Per-step uncertainty quantification (softmax entropy)
  - Route only <75% confidence to async Telegram review thread (not Notion)
  - Log all decisions for drift detection
  
- **Fri:** Deploy AI-only pipeline on fresh 50-event batch:
  - Zero manual labeling
  - Measure precision/recall vs. holdout set
  - If precision >85%, green-light next phase

---

## 3. Next 2â4 Weeks Plan

**Week 2:**
- Integrate on-chain data (Dune/Alchemy) for asset attribution confidence boost
- Build rollback automation: if precision drops <80%, revert to previous model + alert
- Establish Telegram review thread SOP (async, <24h response, structured format)

**Week 3:**
- Run 500-event batch through full AI pipeline
- Measure end-to-end latency, cost per event, false positive rate
- Identify top 3 failure modes â targeted retraining

**Week 4:**
- Freeze labeling; move to continuous evaluation mode
- Prepare event feed schema for TG bot (no trading signals, pure intel)
- Soft-launch internal pilot

---

## 4. Gate for First TG Draft Pilot
