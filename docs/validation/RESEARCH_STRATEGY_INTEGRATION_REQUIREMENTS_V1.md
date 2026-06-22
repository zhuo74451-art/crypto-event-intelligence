# Research Strategy Integration Requirements V1

## Required Inputs

The validation workbench requires the following from the Research Strategy execution lane:

### ResearchHypothesis
```yaml
fields:
  hypothesis_id: str
  research_question: str
  mechanism: str
  testable_prediction: str
  failure_condition: str
  source_references: list[str]
```

### StrategyCandidateProposal
```yaml
fields:
  strategy_candidate_id: str
  hypothesis_id: str
  feature_definitions: list[dict]
  label_spec: dict
  target_regime: str
  time_horizons: list[str]
```

### DatasetSpecification
```yaml
fields:
  dataset_spec_id: str
  source_criteria: dict
  event_type_filter: list[str]
  required_fields: list[str]
```

### ValidationRequirement
```yaml
fields:
  requirement_id: str
  hypothesis_id: str
  required_metrics: list[str]
  minimum_samples: int
  rejection_criteria: str
```

## Not Built Here

This execution lane does NOT:
- Create Trader Profiles
- Write research papers
- Import KOL (Key Opinion Leader) data
- Modify strategy candidates
- Write strategy theory documents
