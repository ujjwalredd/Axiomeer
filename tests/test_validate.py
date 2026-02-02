from marketplace.core.validate import validate_output


class TestValidateOutput:
    def test_valid_payload_with_citations(self):
        payload = {
            "answer": "Some answer",
            "citations": ["https://example.com"],
            "retrieved_at": "2026-01-01T00:00:00Z",
        }
        errors = validate_output(payload, require_citations=True)
        assert errors == []

    def test_missing_citations_when_required(self):
        payload = {"answer": "Some answer"}
        errors = validate_output(payload, require_citations=True)
        assert len(errors) == 2
        assert any("citations" in e.lower() for e in errors)
        assert any("retrieved_at" in e.lower() for e in errors)

    def test_empty_citations_list(self):
        payload = {
            "answer": "Some answer",
            "citations": [],
            "retrieved_at": "2026-01-01T00:00:00Z",
        }
        errors = validate_output(payload, require_citations=True)
        assert len(errors) == 1
        assert "citations" in errors[0].lower()

    def test_citations_not_required(self):
        payload = {"answer": "Some answer"}
        errors = validate_output(payload, require_citations=False)
        assert errors == []

    def test_non_dict_payload(self):
        errors = validate_output("not a dict", require_citations=True)
        assert len(errors) == 1
        assert "json object" in errors[0].lower()

    def test_missing_retrieved_at(self):
        payload = {
            "answer": "Some answer",
            "citations": ["https://example.com"],
        }
        errors = validate_output(payload, require_citations=True)
        assert len(errors) == 1
        assert "retrieved_at" in errors[0].lower()

    def test_empty_string_retrieved_at(self):
        payload = {
            "answer": "Some answer",
            "citations": ["https://example.com"],
            "retrieved_at": "   ",
        }
        errors = validate_output(payload, require_citations=True)
        assert len(errors) == 1
        assert "retrieved_at" in errors[0].lower()

    def test_citations_with_empty_strings(self):
        payload = {
            "answer": "Some answer",
            "citations": ["", "  "],
            "retrieved_at": "2026-01-01T00:00:00Z",
        }
        errors = validate_output(payload, require_citations=True)
        assert len(errors) == 1
        assert "citations" in errors[0].lower()
