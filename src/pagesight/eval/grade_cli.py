"""Blind human grading (Task 6.4): shows 50 sampled dev answers with their question and reference
answer; Kunal types c (correct), p (partial) or i (incorrect). Every grade is saved at once, so the
session can stop and resume. The judge's grades are never shown.

Usage, in your own terminal:
  uv run python -m pagesight.eval.grade_cli results/answers-dev-<time>.json
  -> results/human_grades-dev-<time>.json
"""

import argparse
import json
import random
import sys
from pathlib import Path

from pagesight.config import SEED, SUBSETS
from pagesight.data.vidore import load_queries
from pagesight.eval.runner import RESULTS

SAMPLE = 50
KEYS = {"c": "correct", "p": "partial", "i": "incorrect"}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answers", type=Path)
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(
        encoding="utf-8"
    )  # page text has curly quotes, euro signs, ...
    run = json.loads(args.answers.read_text(encoding="utf-8"))
    queries = {q.id: q for s in SUBSETS for q in load_queries(s)}
    answers = {
        r["query"]: r["answer"]
        for r in run["records"]
        if r["kind"] == "answerable" and r["status"] == "answer"
    }
    chosen = random.Random(SEED).sample(sorted(answers), min(SAMPLE, len(answers)))
    path = RESULTS / f"{run['run_id'].replace('answers-', 'human_grades-')}.json"
    grades = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for n, qid in enumerate(chosen, start=1):
        if qid in grades:
            continue
        q = queries[qid]
        print(f"\n[{n}/{len(chosen)}] {qid}")
        print(f"Question:  {q.text}\nReference: {q.answer}\nAnswer:    {answers[qid]}")
        key = ""
        while key not in (*KEYS, "q"):
            key = (
                input("c = correct, p = partial, i = incorrect, q = quit: ")
                .strip()
                .lower()
            )
        if key == "q":
            break
        grades[qid] = KEYS[key]
        path.write_text(json.dumps(grades, indent=1) + "\n", encoding="utf-8")
    print(f"\n{len(grades)} of {len(chosen)} graded; saved {path}")


if __name__ == "__main__":
    main()
