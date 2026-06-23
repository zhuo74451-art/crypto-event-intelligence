"""Build SQLite index for validation pilot v2."""
import sqlite3, json, pathlib

VD = pathlib.Path("C:/Users/zhuo7/Desktop/crypto-event-intelligence-worktrees/lane-d-validation-walkforward-calibration-v1") / "data" / "intelligence" / "validation" / "pilot_v2"
INDEX_DIR = VD / "indexes"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
DB = INDEX_DIR / "validation_pilot_v2.sqlite"

def load_jsonl(p):
    return [json.loads(l) for l in p.read_text("utf-8").strip().splitlines() if l]

def insert_table(conn, table, records):
    if not records: return
    cols = list(records[0].keys())
    safe = ['"' + c + '"' for c in cols]
    pl = ",".join(["?" for _ in cols])
    conn.execute(f'DROP TABLE IF EXISTS "{table}"')
    conn.execute(f'CREATE TABLE "{table}" ({",".join(safe)})')
    for r in records:
        vals = [json.dumps(v) if isinstance(v, (list, dict)) else v for v in [r.get(c, "") for c in cols]]
        conn.execute(f'INSERT INTO "{table}" VALUES ({pl})', vals)
    c = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    print(f"  {table}: {c}")

conn = sqlite3.connect(str(DB))
tables = [
    ("directional_validation", VD / "datasets" / "directional_validation_dataset_v2.jsonl"),
    ("macro_abstentions", VD / "datasets" / "macro_abstention_dataset_v2.jsonl"),
    ("fold_evaluations", VD / "folds" / "walkforward_fold_evaluations_v2.jsonl"),
    ("baseline_comparisons", VD / "baselines" / "paired_baseline_comparison_v2.jsonl"),
    ("leave_one_unit_out", VD / "evaluations" / "leave_one_release_unit_out_v2.jsonl"),
    ("failed_experiments", VD / "failed_experiments" / "failed_experiments_v2.jsonl"),
]
m = 0
for table, p in tables:
    if p.exists():
        recs = load_jsonl(p)
        insert_table(conn, table, recs)
        dc = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        if dc != len(recs):
            print(f"  MISMATCH: {table}"); m += 1
conn.execute("CREATE INDEX IF NOT EXISTS idx_directional_release_unit ON directional_validation(release_unit_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_directional_horizon ON directional_validation(evaluation_horizon)")
conn.commit(); conn.close()
print(f"Mismatches: {m}")
if m: exit(1)
