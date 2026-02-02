from marketplace.core.cap_extractor import _heuristic_caps


class TestHeuristicCaps:
    def test_weather_keywords(self):
        caps = _heuristic_caps("What is the weather forecast?", force_citations=False)
        assert "weather" in caps

    def test_realtime_keyword_current(self):
        caps = _heuristic_caps("What is the current temperature?", force_citations=False)
        assert "realtime" in caps
        assert "weather" in caps

    def test_realtime_keyword_today(self):
        caps = _heuristic_caps("What is the stock price today?", force_citations=False)
        assert "realtime" in caps
        assert "finance" in caps

    def test_citations_keyword(self):
        caps = _heuristic_caps("Find information and cite sources", force_citations=False)
        assert "citations" in caps

    def test_force_citations(self):
        caps = _heuristic_caps("Calculate 2+2", force_citations=True)
        assert "citations" in caps
        assert "math" in caps

    def test_finance_keywords(self):
        caps = _heuristic_caps("What is the current CPI inflation rate?", force_citations=False)
        assert "finance" in caps

    def test_math_keywords(self):
        caps = _heuristic_caps("Calculate the derivative of x^2", force_citations=False)
        assert "math" in caps

    def test_coding_keywords(self):
        caps = _heuristic_caps("Fix this python bug in my code", force_citations=False)
        assert "coding" in caps

    def test_translate_keywords(self):
        caps = _heuristic_caps("Translate this to spanish", force_citations=False)
        assert "translate" in caps

    def test_summarize_keywords(self):
        caps = _heuristic_caps("Summarize this article", force_citations=False)
        assert "summarize" in caps

    def test_search_keywords(self):
        caps = _heuristic_caps("Search for who is the president", force_citations=False)
        assert "search" in caps

    def test_docs_keywords(self):
        caps = _heuristic_caps("Show me the API documentation", force_citations=False)
        assert "docs" in caps

    def test_multiple_caps(self):
        caps = _heuristic_caps("Search the current weather forecast and cite sources", force_citations=False)
        assert "search" in caps
        assert "weather" in caps
        assert "realtime" in caps
        assert "citations" in caps

    def test_no_caps_for_vague_query(self):
        caps = _heuristic_caps("hello there", force_citations=False)
        assert caps == []

    def test_no_duplicates(self):
        caps = _heuristic_caps("weather forecast temperature rain", force_citations=False)
        assert len(caps) == len(set(caps))
