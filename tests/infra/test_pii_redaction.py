from app.infra.pii_redaction import redact


def test_redact_replaces_name_email_and_phone():
    text = "My name is John Smith, email john.smith@example.com, phone +961 71 234 567."
    result = redact(text)
    assert "John Smith" not in result
    assert "john.smith@example.com" not in result
    assert "+961 71 234 567" not in result
    assert "<EMAIL_ADDRESS>" in result


def test_redact_leaves_plain_math_text_unchanged():
    text = "Solve for x: 2x + 5 = 13."
    assert redact(text) == text
