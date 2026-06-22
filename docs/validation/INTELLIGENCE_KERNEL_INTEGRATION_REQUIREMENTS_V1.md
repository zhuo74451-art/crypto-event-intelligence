# Intelligence Kernel Integration Requirements V1

## Required Contracts

The validation workbench requires the following contract types from the Intelligence Kernel execution lane:

### ValidationPredictionRecord
```yaml
fields:
  prediction_id: str
  event_id: str
  as_of_time: datetime
  horizon: str
  predicted_direction: str  # up/down/flat/unknown
  confidence_score: float
  model_id: str
  strategy_candidate_id: str
  feature_hash: str
  feature_set_version: str
```

### ValidationAssessmentRecord
```yaml
fields:
  assessment_id: str
  event_id: str
  market_regime: str
  evidence_strength: str
  transmission_path: str
  market_confirmation: str
```

### ValidationHypothesisRecord
```yaml
fields:
  hypothesis_id: str
  research_question: str
  testable_prediction: str
  failure_condition: str
  validation_status: str
```

## Stub Location

These contracts exist as conceptual stubs in:
```
market_radar/validation/adapters/__init__.py
```

They are marked:
```yaml
temporary_integration_stub: true
production_contract_owner: intelligence_kernel
```

## Not Built Here

This execution lane does NOT create production implementations of:
- MarketAssessment
- StrategyPack
- MarketHypothesisInstance
- ConfidenceStatement
- ArbitrationEngine
