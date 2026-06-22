#!/usr/bin/env python3
"""
Build Question Registry — generates open research questions from conflicts and evidence gaps.
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


def generate_questions_from_conflicts(conflicts_path: str, questions_path: str):
    """Generate research questions from unresolved conflicts."""
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    from market_radar.intelligence.research.contracts import ResearchQuestionV1

    questions = []
    if not os.path.isfile(conflicts_path):
        print(f"No conflicts file at {conflicts_path}")
        return

    with open(conflicts_path) as f:
        for line in f:
            conflict = json.loads(line)
            q = ResearchQuestionV1(
                question_key=f"resolve_{conflict['conflict_key']}",
                question_text=f"Resolve {conflict['conflict_type']} between claims {conflict['claim_ids']}",
                status="open",
                linked_conflict_set_ids=[conflict["conflict_set_id"]],
                linked_claim_ids=conflict["claim_ids"],
                priority=3,
                owner_module="research_intelligence",
            )
            questions.append(q)

    with open(questions_path, "w") as f:
        for q in questions:
            f.write(json.dumps(q.to_dict(), ensure_ascii=False) + "\n")
    print(f"Generated {len(questions)} questions → {questions_path}")


def main():
    parser = argparse.ArgumentParser(description="Build Research Question Registry")
    parser.add_argument("--conflicts-path", default="data/intelligence/research/conflicts/conflict_sets_v1.jsonl")
    parser.add_argument("--questions-output", default="data/intelligence/research/questions/research_questions_v1.jsonl")
    args = parser.parse_args()

    conflicts_path = os.path.join(PROJECT_ROOT, args.conflicts_path)
    questions_path = os.path.join(PROJECT_ROOT, args.questions_output)

    generate_questions_from_conflicts(conflicts_path, questions_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
