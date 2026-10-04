import pytest

from pagesight.eval.answers import answer_metrics


def rec(kind: str, status: str, gold_shown: bool, citations_gold: bool | None = None):
    return {
        "kind": kind,
        "status": status,
        "gold_shown": gold_shown,
        "citations_gold": citations_gold,
    }


RECORDS = [
    rec("answerable", "answer", True, citations_gold=True),
    rec("answerable", "answer", True, citations_gold=False),
    rec("answerable", "not_found", True),  # refused although a gold page was shown
    rec("answerable", "not_found", False),  # no gold page shown: a fair refusal
    rec("answerable", "invalid", False),
    rec("abstain", "not_found", False),
    rec("abstain", "answer", False, citations_gold=False),
]


def test_answer_metrics_by_hand():
    m = answer_metrics(RECORDS)
    assert m["answerable"] == 5 and m["abstain"] == 2
    assert m["answered"] == pytest.approx(2 / 5)
    assert m["invalid"] == pytest.approx(1 / 5)
    # 3 answerable records showed a gold page; 1 of them was refused
    assert m["wrong_not_found"] == pytest.approx(1 / 3)
    assert m["citation_accuracy"] == pytest.approx(1 / 2)
    assert m["abstention_recall"] == pytest.approx(1 / 2)
    # 3 NOT_FOUNDs in total; 2 of them had no gold page in view
    assert m["not_found_precision"] == pytest.approx(2 / 3)


def test_empty_groups_give_none_not_a_division_error():
    m = answer_metrics([rec("answerable", "invalid", False)])
    assert m["citation_accuracy"] is None and m["abstention_recall"] is None
    assert m["wrong_not_found"] is None and m["not_found_precision"] is None
