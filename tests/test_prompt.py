from PIL import Image

from pagesight.answer.prompt import build_messages, parse

PAGES = ["hr-419", "hr-493"]


def test_exact_not_found_is_an_abstention():
    assert parse("  NOT_FOUND\n", PAGES).status == "not_found"


def test_answer_needs_a_citation_of_a_shown_page():
    parsed = parse("Switzerland has the highest rate, 12% [p:hr-419].", PAGES)
    assert parsed.status == "answer"
    assert parsed.text == "Switzerland has the highest rate, 12%."
    assert parsed.citations == ["hr-419"]


def test_citations_are_unique_and_in_order():
    parsed = parse("A [p:hr-493] and B [p:hr-419] [p:hr-493]", PAGES)
    assert parsed.citations == ["hr-493", "hr-419"]


def test_malformed_outputs_are_invalid():
    for output in [
        "Switzerland, 12%.",  # no citation
        "Switzerland, 12% [p:hr-999].",  # page that was not shown
        "Switzerland [p:hr-419] and [p:132].",  # one bad citation spoils the answer
        "The answer is NOT_FOUND.",  # NOT_FOUND must stand alone
        "NOT_FOUND [p:hr-419]",
        "[p:hr-419]",  # citation without an answer
        "",
    ]:
        assert parse(output, PAGES).status == "invalid", output


def test_each_image_is_preceded_by_its_page_label_and_the_question_comes_last():
    # stand-ins: the builder only places them (a str would mean page text)
    images = [Image.new("RGB", (1, 1)), Image.new("RGB", (1, 1))]
    messages = build_messages("Which country?", PAGES, images)
    system, user = messages
    assert system["role"] == "system" and "UNTRUSTED" in system["content"][0]["text"]
    content = user["content"]
    assert [c["type"] for c in content] == ["text", "image", "text", "image", "text"]
    assert content[0]["text"] == "Page [p:hr-419]:" and content[1]["image"] is images[0]
    assert content[2]["text"] == "Page [p:hr-493]:" and content[3]["image"] is images[1]
    question, rules = content[4]["text"].split("\n\n")
    assert question == "Question: Which country?"
    assert "[p:hr-419]" in rules and "NOT_FOUND" in rules


def test_gate_shows_the_same_pages_and_asks_yes_or_no_last():
    from pagesight.answer.prompt import build_gate_messages

    images = [Image.new("RGB", (1, 1)), Image.new("RGB", (1, 1))]
    _, user = build_gate_messages("Which country?", PAGES, images)
    content = user["content"]
    assert [c["type"] for c in content] == ["text", "image", "text", "image", "text"]
    question, rule = content[4]["text"].split("\n\n")
    assert question == "Question: Which country?"
    assert "YES" in rule and "NO" in rule and "NOT_FOUND" not in rule


def test_text_pages_are_sent_as_text_items_after_their_ids():
    # the Compare tab's text-RAG side (D-045) uses the same prompt with page text instead of images
    content = build_messages("Q?", ["hr-1"], ["Revenue 42"])[1]["content"]

    assert content[:2] == [
        {"type": "text", "text": "Page [p:hr-1]:"},
        {"type": "text", "text": "Revenue 42"},
    ]
