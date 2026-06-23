"""Build and export strategy definitions to JSON."""
import json, sys
sys.path.insert(0, ".")
from market_radar.intelligence.strategy_replay.strategies import ALL_MACRO_STRATEGIES


def build(output_path: str):
    definitions = [s.to_dict() for s in ALL_MACRO_STRATEGIES.values()]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(definitions, f, indent=2, ensure_ascii=False)
    print(f"Written {len(definitions)} definitions to {output_path}")


if __name__ == "__main__":
    build("data/intelligence/strategy_replay/definitions/strategy_definitions_v1.json")
