from marketplace.core.cap_extractor import extract_capabilities
import marketplace.core.cap_extractor as cap_extractor


class TestLLMOnlyCaps:
    def test_valid_json_caps(self, monkeypatch):
        monkeypatch.setattr(
            cap_extractor,
            "ollama_generate",
            lambda model, prompt: '{"capabilities":["weather","citations","unknown"]}',
        )
        caps = extract_capabilities("Weather?", force_citations=False)
        assert "weather" in caps
        assert "citations" in caps
        assert "unknown" not in caps

    def test_invalid_json_returns_empty(self, monkeypatch):
        monkeypatch.setattr(cap_extractor, "ollama_generate", lambda model, prompt: "not json")
        caps = extract_capabilities("Weather?", force_citations=False)
        assert caps == []

    def test_non_list_caps_returns_empty(self, monkeypatch):
        monkeypatch.setattr(cap_extractor, "ollama_generate", lambda model, prompt: '{"capabilities":"weather"}')
        caps = extract_capabilities("Weather?", force_citations=False)
        assert caps == []
