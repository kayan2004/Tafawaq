from verdict import InputVerdict, OutputVerdict, parse_input_verdict, parse_output_verdict


def test_parse_input_verdict_valid_category():
    raw = '{"category": "prompt_injection", "score": 0.91, "reason": "ignore instructions"}'
    assert parse_input_verdict(raw) == InputVerdict(
        category="prompt_injection", score=0.91, reason="ignore instructions"
    )


def test_parse_input_verdict_null_category():
    raw = '{"category": null, "score": 0.0, "reason": ""}'
    assert parse_input_verdict(raw) == InputVerdict(category=None, score=0.0, reason="")


def test_parse_input_verdict_strips_markdown_fences():
    raw = '```json\n{"category": "off_topic", "score": 0.8, "reason": "basketball"}\n```'
    assert parse_input_verdict(raw) == InputVerdict(category="off_topic", score=0.8, reason="basketball")


def test_parse_input_verdict_unknown_category_treated_as_none():
    raw = '{"category": "made_up_category", "score": 0.5, "reason": "x"}'
    assert parse_input_verdict(raw).category is None


def test_parse_input_verdict_fails_closed_on_garbage():
    verdict = parse_input_verdict("not json at all")
    assert verdict.category == "harmful_content"
    assert verdict.score == 1.0


def test_parse_output_verdict_valid():
    raw = '{"flagged": true, "score": 0.7, "reason": "inappropriate scenario"}'
    assert parse_output_verdict(raw) == OutputVerdict(flagged=True, score=0.7, reason="inappropriate scenario")


def test_parse_output_verdict_fails_closed_on_garbage():
    verdict = parse_output_verdict("garbage")
    assert verdict.flagged is True
    assert verdict.score == 1.0
