"""Build kernel packages from existing replay results and hypotheses."""
import json, sys, argparse
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.kernel_adapter import compute_kernel_package_id


def build(hypotheses_path: str, output_path: str):
    count = 0
    with open(hypotheses_path, "r", encoding="utf-8") as fi,          open(output_path, "w", encoding="utf-8") as fo:
        for line in fi:
            h = json.loads(line)
            kp_id = compute_kernel_package_id(h.get("event_id", ""), [h.get("strategy_id", "")], [h.get("hypothesis_id", "")])
            fo.write(json.dumps({"kernel_package_id": kp_id, "hypothesis": h}, ensure_ascii=False) + "\n")
            count += 1
    print(f"Built {count} kernel packages to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hypotheses", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    build(args.hypotheses, args.output)
