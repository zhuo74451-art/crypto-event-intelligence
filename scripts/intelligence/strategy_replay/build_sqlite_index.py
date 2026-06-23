"""Build SQLite index for pilot v2 outputs."""
import sqlite3, json, pathlib, hashlib

WORKTREE = pathlib.Path(r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-c-macro-strategy-replay-v1")
D = WORKTREE / "data" / "intelligence" / "strategy_replay" / "pilot_v2"
INDEX_DIR = WORKTREE / "data" / "intelligence" / "strategy_replay" / "indexes"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
DB = INDEX_DIR / "strategy_replay_pilot_v2.sqlite"

def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]

def insert_table(conn, table, records):
    if not records:
        print(f"  {table}: 0 records (empty)")
        return
    cols = list(records[0].keys())
    safe_cols = [f'"{c}"' for c in cols]
    conn.execute(f"DROP TABLE IF EXISTS \"{table}\"")
    conn.execute(f"CREATE TABLE \"{table}\" ({",".join(safe_cols)})")
    for r in records:
        vals = [json.dumps(v) if isinstance(v, (list, dict)) else v for v in [r.get(c, "") for c in cols]]
        conn.execute(f"INSERT INTO \"{table}\" VALUES ({",".join(["?" for _ in cols])})", vals)
    count = conn.execute(f"SELECT COUNT(*) FROM \"{table}\"").fetchone()[0]
    print(f"  {table}: {count} records")

conn = sqlite3.connect(str(DB))
tables = [
    ("release_units", "release_units_v1.jsonl"),
    ("decision_inputs", "decision_inputs_v1.jsonl"),
    ("macro_abstentions", "macro_abstention_records_v1.jsonl"),
    ("replay_results", "strategy_replay_results_v2.jsonl"),
    ("hypotheses", "strategy_hypotheses_v2.jsonl"),
    ("kernel_packages", "kernel_input_packages_v2.jsonl"),
    ("evaluation_outcomes", "evaluation_outcomes_v1.jsonl"),
    ("strategy_evaluations", "strategy_evaluations_v1.jsonl"),
    ("baseline_evaluations", "baseline_evaluations_v1.jsonl"),
]

mismatches = 0
for table, fname in tables:
    p = D / fname
    if p.exists():
        records = load_jsonl(p)
        insert_table(conn, table, records)
        fc = len(records)
        dc = conn.execute(f"SELECT COUNT(*) FROM \"{table}\"").fetchone()[0]
        if fc != dc:
            print(f"  MISMATCH: {table}: file={fc} db={dc}")
            mismatches += 1
    else:
        print(f"  {table}: FILE NOT FOUND: {fname}")

conn.commit()
conn.close()
print(f"File-SQLite count mismatches: {mismatches}")
if mismatches:
    exit(1)
