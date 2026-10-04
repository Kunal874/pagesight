"""Answer judge (Task 6.4, D-034): Qwen3.5-4B, text only, grades each answer against the reference
answer as correct, partial or incorrect. It never sees the pages. With --human it does not judge
again: it adds agreement % and Cohen's kappa between the stored judge grades and Kunal's blind
grades to the judge results (the judge is trusted only if kappa >= 0.6).

Usage: uv run python -m pagesight.eval.judge results/answers-<split>-<time>.json
           [--human results/human_grades-<split>-<time>.json]
       -> results/judge-<split>-<time>.json
"""

import argparse
import json
from pathlib import Path

from pagesight.answer.vlm import MODEL, REVISION, AnswerModel
from pagesight.config import SUBSETS
from pagesight.data.vidore import load_queries
from pagesight.eval.answers import share
from pagesight.eval.metrics import cohen_kappa
from pagesight.eval.runner import RESULTS, git_state

RUBRIC = (
    "You grade an answer to a question against a reference answer.\n"
    "CORRECT: the answer gives the key facts of the reference (numbers, names, direction of "
    "change) and contradicts nothing in it; extra correct detail is fine.\n"
    "PARTIAL: some key facts are right, but others are missing or wrong.\n"
    "INCORRECT: the key facts are wrong or missing, or it answers a different question.\n"
    "Reply with one word: CORRECT, PARTIAL or INCORRECT."
)
GRADES = {"CORRECT": "correct", "PARTIAL": "partial", "INCORRECT": "incorrect"}


def judge_messages(question: str, reference: str, answer: str) -> list[dict]:
    text = (
        f"{RUBRIC}\n\nQuestion: {question}\nReference answer: {reference}\n"
        f"Answer to grade: {answer}\n\nGrade:"
    )
    return [{"role": "user", "content": [{"type": "text", "text": text}]}]


def parse_judgement(text: str) -> str | None:
    words = text.split()
    return GRADES.get(words[0].strip(".:,;!").upper()) if words else None


def accuracy(records: list[dict], grades: dict[str, str | None]) -> dict:
    """Over answerable queries: NOT_FOUND and invalid outputs count as not correct."""
    ans = [r for r in records if r["kind"] == "answerable"]
    labels = [grades.get(r["query"]) if r["status"] == "answer" else "no" for r in ans]
    return {
        "correct": share(labels.count("correct"), len(ans)),
        "partial": share(labels.count("partial"), len(ans)),
        "ungraded": share(labels.count(None), len(ans)),
    }


def agreement(judge: dict[str, str | None], human: dict[str, str]) -> dict:
    """Over the answers both graded (the judge leaves unparseable replies ungraded)."""
    both = sorted(q for q in human if judge.get(q))
    pairs = [judge[q] for q in both], [human[q] for q in both]
    agree = sum(x == y for x, y in zip(*pairs, strict=True))
    return {
        "n": len(both),
        "percent": 100 * share(agree, len(both)),
        "cohen_kappa": cohen_kappa(*pairs),
        "git": git_state(),
    }


def judge_run(run: dict) -> dict:
    queries = {q.id: q for s in SUBSETS for q in load_queries(s)}
    to_grade = [
        r
        for r in run["records"]
        if r["kind"] == "answerable" and r["status"] == "answer"
    ]
    vlm, grades = AnswerModel(), {}
    for n, r in enumerate(to_grade, start=1):
        q = queries[r["query"]]
        reply = vlm.generate(
            judge_messages(q.text, q.answer, r["answer"]), max_new_tokens=8
        )
        grades[r["query"]] = parse_judgement(reply)
        print(
            f"{n}/{len(to_grade)} {r['query']} {grades[r['query']]} {reply.strip()[:40]!r}"
        )
    vlm.unload()
    result = {
        "run_id": run["run_id"].replace("answers-", "judge-"),
        "answers_run": run["run_id"],
        "model": MODEL,
        "revision": REVISION,
        "git": git_state(),
        "accuracy": {
            "all": accuracy(run["records"], grades),
            **{
                s: accuracy([r for r in run["records"] if r["subset"] == s], grades)
                for s in SUBSETS
            },
        },
        "grades": grades,
    }
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answers", type=Path)
    parser.add_argument("--human", type=Path)
    args = parser.parse_args(argv)
    run = json.loads(args.answers.read_text(encoding="utf-8"))
    path = RESULTS / f"{run['run_id'].replace('answers-', 'judge-')}.json"
    if args.human:
        # the stored grades: agreement must describe the very grades the report uses
        result = json.loads(path.read_text(encoding="utf-8"))
        human = json.loads(args.human.read_text(encoding="utf-8"))
        result["agreement"] = agreement(result["grades"], human)
    else:
        result = judge_run(run)
    shown = {k: result[k] for k in result if k in ("accuracy", "agreement")}
    print(json.dumps(shown, indent=1))
    path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"saved results/{path.name}")


if __name__ == "__main__":
    main()
