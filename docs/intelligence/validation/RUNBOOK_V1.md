# Runbook V1

## Pipeline Execution
```powershell
python -X utf8 scripts/intelligence/validation/run_lane_d_pipeline.py ^
    --replay-results data/intelligence/validation/cache/lane_c_inputs/strategy_replay_results_v1.jsonl ^
    --baseline-results data/intelligence/validation/cache/lane_c_inputs/baseline_replay_results_v1.jsonl ^
    --abstentions data/intelligence/validation/cache/lane_c_inputs/abstention_records_v1.jsonl ^
    --output-dir data/intelligence/validation
```

## Running Tests
```powershell
python -X utf8 -m pytest tests/intelligence/validation/ -v
```
