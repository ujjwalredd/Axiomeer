from marketplace.core.evidence_quality import assess_evidence


class TestAssessEvidence:
    def test_high_quality_with_citations(self):
        payload = {
            "answer": "Temperature is 5C",
            "citations": ["https://open-meteo.com/"],
            "quality": "verified",
        }
        quality, reasons = assess_evidence(payload)
        assert quality == "HIGH"

    def test_low_quality_mock(self):
        payload = {
            "answer": "Temperature is 5C",
            "citations": ["mock://provider"],
            "quality": "mock",
        }
        quality, reasons = assess_evidence(payload)
        assert quality == "LOW"
        assert any("mock" in r.lower() for r in reasons)

    def test_low_quality_simulated(self):
        payload = {
            "answer": "Temperature is 5C",
            "citations": ["https://example.com"],
            "quality": "simulated",
        }
        quality, reasons = assess_evidence(payload)
        assert quality == "LOW"

    def test_low_quality_fake(self):
        payload = {
            "answer": "Some data",
            "citations": ["https://example.com"],
            "quality": "fake",
        }
        quality, reasons = assess_evidence(payload)
        assert quality == "LOW"

    def test_low_quality_test(self):
        payload = {
            "answer": "Some data",
            "citations": ["https://example.com"],
            "quality": "test",
        }
        quality, reasons = assess_evidence(payload)
        assert quality == "LOW"

    def test_low_quality_mock_data_in_answer(self):
        payload = {
            "answer": "This is mock data for testing",
            "citations": ["https://example.com"],
        }
        quality, reasons = assess_evidence(payload)
        assert quality == "LOW"
        assert any("mock" in r.lower() or "simulated" in r.lower() for r in reasons)

    def test_low_quality_no_citations(self):
        payload = {"answer": "Some answer"}
        quality, reasons = assess_evidence(payload)
        assert quality == "LOW"
        assert any("citations" in r.lower() for r in reasons)

    def test_low_quality_empty_citations(self):
        payload = {
            "answer": "Some answer",
            "citations": [],
        }
        quality, reasons = assess_evidence(payload)
        assert quality == "LOW"

    def test_non_dict_payload(self):
        quality, reasons = assess_evidence("not a dict")
        assert quality == "LOW"
        assert any("json" in r.lower() for r in reasons)

    def test_low_quality_dummy_in_answer(self):
        payload = {
            "answer": "This uses dummy values",
            "citations": ["https://example.com"],
        }
        quality, reasons = assess_evidence(payload)
        assert quality == "LOW"
