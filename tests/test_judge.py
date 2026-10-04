from pagesight.eval.judge import accuracy, judge_messages, parse_judgement


def test_the_first_word_decides_the_grade():
    assert parse_judgement("CORRECT") == "correct"
    assert parse_judgement(" partial\n") == "partial"
    assert (
        parse_judgement("INCORRECT. The answer names the wrong country.") == "incorrect"
    )


def test_anything_else_is_ungraded():
    for text in ["", "The answer is correct.", "MOSTLY CORRECT", "correct-ish"]:
        assert parse_judgement(text) is None, text


def test_judge_sees_question_reference_and_answer_but_no_pages():
    (message,) = judge_messages(
        "Which country?", "Switzerland, 12%.", "Swiss, 12% [p:hr-1]"
    )
    text = message["content"][0]["text"]
    assert "Which country?" in text and "Switzerland, 12%." in text
    assert "Swiss, 12% [p:hr-1]" in text
    assert all(part["type"] == "text" for part in message["content"])


def test_accuracy_counts_refusals_and_invalid_outputs_as_not_correct():
    records = [
        {"query": "q1", "kind": "answerable", "status": "answer"},
        {"query": "q2", "kind": "answerable", "status": "answer"},
        {"query": "q3", "kind": "answerable", "status": "not_found"},
        {"query": "q4", "kind": "answerable", "status": "invalid"},
        {"query": "q1", "kind": "abstain", "status": "answer"},  # not part of accuracy
    ]
    acc = accuracy(records, {"q1": "correct", "q2": "partial"})
    assert acc == {"correct": 0.25, "partial": 0.25, "ungraded": 0.0}


def test_agreement_skips_answers_the_judge_could_not_grade():
    from pagesight.eval.judge import agreement

    judge = {"q1": "correct", "q2": "partial", "q3": None, "q4": "incorrect"}
    human = {"q1": "correct", "q2": "incorrect", "q3": "correct", "q4": "incorrect"}
    a = agreement(judge, human)
    # q1, q2, q4 are compared and 2 agree; judge c/p/i vs human c/i/i:
    # p_o = 2/3, p_e = 1/3 * 1/3 + 1/3 * 2/3 = 1/3, kappa = (1/3) / (2/3)
    assert a["n"] == 3
    assert round(a["percent"], 2) == 66.67
    assert round(a["cohen_kappa"], 4) == 0.5
